"""
What the orchestrator reports when a generation run ends.

The old code always emitted {"type": "pipeline_complete"} once every wave had
run, whether or not agents failed. The frontend took that at face value and
showed "Prototype ready — open it in Prototype Viewer" side by side with
Prototype FAILED at 0% — the exact screenshot from a live demo run where the
API agent failed and five agents fell with it.

The verdict emitted at the end must match the states: complete only when
every agent completed, and an explicit "pipeline_failed" naming the failed
agents otherwise. The states dict is returned either way, so persistence
(write-through of whatever output exists) is unaffected.

Run from the backend/ directory:
    python -m unittest tests.test_orchestrator_pipeline -v
"""

import asyncio
import logging
import unittest
from unittest import mock

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from app.agents import orchestrator  # noqa: E402
from app.agents.state import AgentStatus  # noqa: E402
from app.llm.providers.base import ChatResult  # noqa: E402

logging.getLogger("protopilot.agents").setLevel(logging.CRITICAL)


class _FakeRouter:
    """
    Stand-in for the llm_router singleton. Returns a canned result for every
    agent except the one named in `failing`, which raises — exactly what a
    provider outage does inside run_one().
    """

    def __init__(self, failing: str | None):
        self.failing = failing
        self.calls: list[str] = []

    async def chat(self, messages, max_tokens=None, temperature=None, max_rate_limit_wait=None):
        # Mirror the real llm_router.chat signature exactly — the orchestrator
        # now passes max_rate_limit_wait for the generation path, and a fake
        # that rejected the kwarg would fail every agent with a TypeError
        # instead of exercising the verdict logic this test is about.
        system = next((m["content"] for m in messages if m.get("role") == "system"), "")
        # Which agent is this? The system prompt is the definition's; the
        # agents we care about are identified by a marker in the fake result.
        self.calls.append(system[:40])
        if self.failing and system.startswith("You are the API Layer agent.") and self.failing == "api":
            raise RuntimeError("All LLM providers failed or are unavailable. groq: rate limited (429)")
        return ChatResult(
            text=f"output for {system[:20]!r}",
            provider="stub", model="stub", input_tokens=1, output_tokens=1,
        )


class OrchestratorVerdictTest(unittest.IsolatedAsyncioTestCase):
    REQUIREMENTS = [{"title": "Food delivery app", "category": "General", "priority": "Medium"}]

    async def _run(self, failing: str | None):
        events: list[dict] = []

        async def emit(event: dict):
            events.append(event)

        fake_router = _FakeRouter(failing=failing)
        with mock.patch.object(orchestrator, "llm_router", fake_router), \
             mock.patch.object(
                 orchestrator.stitch_service, "generate_prototype_html",
                 new=mock.AsyncMock(return_value=None),
             ):
            states = await orchestrator.run_pipeline(self.REQUIREMENTS, emit)
        return events, states

    async def test_a_clean_run_still_says_complete(self):
        events, states = await self._run(failing=None)

        self.assertEqual(events[-1], {"type": "pipeline_complete"})
        self.assertFalse(
            any(e["type"] == "pipeline_failed" for e in events),
            "a run where every agent completed is a success, not a failure",
        )
        self.assertEqual(
            {s.status for s in states.values()}, {AgentStatus.COMPLETED},
            "all nine agents must land on completed",
        )

    async def test_a_failed_agent_ends_with_pipeline_failed(self):
        events, states = await self._run(failing="api")

        last = events[-1]
        self.assertEqual(last["type"], "pipeline_failed")
        self.assertIn("api", last["message"])
        self.assertNotIn("pipeline_complete", [e["type"] for e in events],
                         "a run with failures must never claim completion")

        # The cascade: everything downstream of api is skipped or failed, so
        # the prototype — the thing the demo exists to produce — did not run.
        self.assertEqual(states["prototype"].status, AgentStatus.FAILED)
        self.assertIn("Skipped", " ".join(states["prototype"].logs))

    async def test_the_failure_message_names_every_failed_agent(self):
        events, states = await self._run(failing="api")

        message = events[-1]["message"]
        # The six agents that fell with api: api itself (real failure),
        # ui and backend (skipped — both depend on api), qa (depends on
        # ui+backend), devops (depends on qa), prototype (depends on ui+api).
        # Their names must be in the message, not a generic "some agents
        # failed".
        failed_ids = [aid for aid, s in states.items() if s.status == AgentStatus.FAILED]
        self.assertEqual(len(failed_ids), 6)
        for agent_id in failed_ids:
            self.assertIn(agent_id, message)


class OrchestratorConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    """
    The generation pipeline must not fire concurrent provider calls.

    ui and backend share a wave, so without serialisation both of their LLM
    calls land in the same instant. On a free tier that splits the per-minute
    token budget between them and one comes back 429/overloaded — the exact
    failure seen twice in the live proof run, where backend failed (and qa +
    devops were skipped under it) while its wave-mate ui succeeded.
    """

    REQUIREMENTS = [{"title": "Food delivery app", "category": "General", "priority": "Medium"}]

    async def test_generation_llm_calls_run_one_at_a_time(self):
        in_flight = 0
        max_in_flight = 0

        async def emit(event: dict):
            pass

        class _ConcurrencyProbeRouter:
            async def chat(self, messages, max_tokens=None, temperature=None, max_rate_limit_wait=None):
                nonlocal in_flight, max_in_flight
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
                # Hold the "call" open briefly so a second concurrent call would
                # overlap it if the pipeline allowed one — the llm_gate is what
                # must stop that. Paired with _WAVE_STAGGER_SECONDS=0 below so
                # wave-mates genuinely start together and the test would fail if
                # the serialisation were removed.
                await asyncio.sleep(0.02)
                in_flight -= 1
                return ChatResult(
                    text="ok", provider="stub", model="stub", input_tokens=1, output_tokens=1,
                )

        with mock.patch.object(orchestrator, "llm_router", _ConcurrencyProbeRouter()), \
             mock.patch.object(orchestrator, "_WAVE_STAGGER_SECONDS", 0), \
             mock.patch.object(
                 orchestrator.stitch_service, "generate_prototype_html",
                 new=mock.AsyncMock(return_value=None),
             ):
            states = await orchestrator.run_pipeline(self.REQUIREMENTS, emit)

        self.assertEqual(
            max_in_flight, 1,
            "generation LLM calls must run one at a time so wave-mates don't "
            "split a free tier's per-minute budget and 429 each other",
        )
        # Serialising must not change the outcome — every agent still completes.
        self.assertEqual(
            {s.status for s in states.values()}, {AgentStatus.COMPLETED},
            "the whole pipeline still succeeds when its LLM calls are serialised",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
