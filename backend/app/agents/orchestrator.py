"""
Runs the AI Workforce pipeline: PM -> Architect -> Database -> API ->
{UI, Backend} -> QA -> DevOps.

Each agent's LLM call includes only the outputs of the agents it directly
depends on (not the whole history) — keeps context small and cost low,
same principle as the requirement extractor.

The "prototype" agent is special: it first tries Google Stitch (see
app/services/stitch_service.py) for a proper high-fidelity UI. Only if
Stitch isn't configured or fails does it fall back to the original
approach of asking a small LLM to hand-write the HTML directly.
"""

import asyncio
import logging
import re
from typing import Awaitable, Callable

from app.agents.definitions import AGENT_DEFINITIONS, EXECUTION_WAVES
from app.agents.state import AgentState, AgentStatus
from app.config import settings
from app.llm.router import llm_router
from app.services import stitch_service

logger = logging.getLogger("protopilot.agents")

# Delay added per agent position within a wave, to keep a wave from arriving at
# a free-tier per-minute ceiling as one burst. The widest wave today is two
# agents (ui + backend), so in practice this adds 0.2s to a generation run.
_WAVE_STAGGER_SECONDS = 0.2

EmitFn = Callable[[dict], Awaitable[None]]


def _strip_markdown_fences(text: str) -> str:
    """
    Some models wrap output in ```html ... ``` fences even when told not to.
    Strips them if present; leaves text untouched otherwise.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def _build_requirements_block(requirements: list[dict]) -> str:
    lines = [f"- [{r['priority']}] {r['title']} ({r['category']})" for r in requirements]
    return "\n".join(lines) if lines else "(no approved requirements yet)"


def _build_context(agent_id: str, states: dict[str, AgentState], requirements_block: str) -> str:
    definition = AGENT_DEFINITIONS[agent_id]

    if not definition.depends_on:
        # Only the PM agent has no dependencies — it works from requirements directly.
        return f"Approved requirements:\n{requirements_block}"

    parts = []
    for dep_id in definition.depends_on:
        dep_state = states[dep_id]
        dep_name = AGENT_DEFINITIONS[dep_id].name
        parts.append(f"--- Output from {dep_name} ---\n{dep_state.output or '(no output)'}")

    return "\n\n".join(parts)


async def run_pipeline(
    requirements: list[dict],
    emit: EmitFn,
) -> dict[str, AgentState]:
    """
    Runs every agent to completion (or failure) in dependency order.
    Returns the final states dict (agent_id -> AgentState), including
    each agent's .output text — useful for a later "generate files" phase.
    """
    states: dict[str, AgentState] = {
        agent_id: AgentState(id=agent_id, name=definition.name, depends_on=definition.depends_on)
        for agent_id, definition in AGENT_DEFINITIONS.items()
    }
    requirements_block = _build_requirements_block(requirements)

    # Serialise the pipeline's LLM calls so concurrent wave-mates (ui + backend
    # share a wave) don't fire simultaneous provider calls that split a free
    # tier's per-minute token budget and knock each other into a 429/overload —
    # the failure that took out the backend agent and everything downstream in
    # the live run. Created here (not at module scope) so it binds to this
    # call's event loop and each run gets a fresh one. See
    # settings.llm_generation_concurrency.
    llm_gate = asyncio.Semaphore(max(1, settings.llm_generation_concurrency))

    async def run_one(agent_id: str):
        state = states[agent_id]
        definition = AGENT_DEFINITIONS[agent_id]

        # If any dependency failed, skip this agent rather than working from broken context.
        if any(states[dep].status == AgentStatus.FAILED for dep in definition.depends_on):
            state.status = AgentStatus.FAILED
            state.logs.append("Skipped — a dependency failed.")
            await emit({"type": "agent_update", **state.to_event_dict()})
            await emit({"type": "agent_log", "agent": agent_id, "message": state.logs[-1]})
            return

        state.status = AgentStatus.THINKING
        state.progress = 10
        await emit({"type": "agent_update", **state.to_event_dict()})
        await emit({"type": "agent_log", "agent": agent_id, "message": f"Reviewing input from: {', '.join(definition.depends_on) or 'requirements'}"})

        context = _build_context(agent_id, states, requirements_block)

        state.status = AgentStatus.WORKING
        state.progress = 50
        await emit({"type": "agent_update", **state.to_event_dict()})

        try:
            if agent_id == "prototype":
                state.output = await _run_prototype_agent(context, definition, emit, agent_id, llm_gate)
            else:
                # One provider call at a time across the whole pipeline — see
                # llm_gate above.
                async with llm_gate:
                    result = await llm_router.chat(
                        messages=[
                            {"role": "system", "content": definition.system_prompt},
                            {"role": "user", "content": context},
                        ],
                        max_tokens=definition.max_tokens,
                        temperature=0.3,
                        # Generation is expected to take a minute or two, so it
                        # is worth waiting out a provider's honest Retry-After
                        # (Groq's live 429s asked ~24s) rather than failing this
                        # agent and cascading every agent that depends on it.
                        # The caption path keeps its short default ceiling.
                        max_rate_limit_wait=settings.llm_generation_max_rate_limit_wait,
                    )
                state.output = result.text.strip()

            state.status = AgentStatus.COMPLETED
            state.progress = 100
            state.logs.append("Completed.")
            await emit({"type": "agent_update", **state.to_event_dict()})
            await emit({
                "type": "agent_output",
                "agent": agent_id,
                "output": state.output,
            })
        except Exception as e:  # noqa: BLE001
            # RuntimeError is the expected "all providers failed" from the
            # router, but a single agent hitting any unexpected error must
            # still fail only ITSELF, not tear down the whole asyncio.gather
            # for its wave and take the agents that would have succeeded with
            # it. Its dependents are skipped (dependency-failed) as usual, and
            # the run ends in pipeline_failed with this agent named — never a
            # false pipeline_complete. logger.exception keeps the traceback for
            # anything that isn't the ordinary provider-exhausted RuntimeError.
            if isinstance(e, RuntimeError):
                logger.warning("agent %s failed: %s", agent_id, e)
            else:
                logger.exception("agent %s failed with an unexpected error", agent_id)
            state.status = AgentStatus.FAILED
            state.progress = 0
            state.logs.append(f"Failed: {e}")
            await emit({"type": "agent_update", **state.to_event_dict()})
            await emit({"type": "agent_log", "agent": agent_id, "message": state.logs[-1]})

    async def run_wave(wave):
        """
        Everything in a wave still runs concurrently — that is the point of the
        DAG — but each agent's first request is offset slightly.

        This is a cushion, not the fix. The waves are mostly one agent wide
        (only ui+backend share one), so the 429 in the live run came from the
        RATE of sequential calls each spending ~1600 output tokens, not from a
        burst. The real fix is the router retrying a 429 instead of writing the
        provider off for 60s — that cooldown is what failed UI, Backend, QA,
        DevOps and Prototype in one go. This offset only keeps the single
        shared wave from landing in the same instant; widest wave is two, so it
        costs 0.2s.
        """
        async def staggered(index, agent_id):
            if index:
                await asyncio.sleep(_WAVE_STAGGER_SECONDS * index)
            await run_one(agent_id)

        await asyncio.gather(*(staggered(i, a) for i, a in enumerate(wave)))

    for wave in EXECUTION_WAVES:
        await run_wave(wave)

    failed = [a for a, s in states.items() if s.status == AgentStatus.FAILED]
    if failed:
        # An agent failed — say so instead of claiming victory. The old
        # "pipeline_complete" made the frontend show "Prototype ready — open
        # it in Prototype Viewer" while the Prototype agent sat FAILED at 0%,
        # which is the worst possible lie to tell judges.
        await emit({
            "type": "pipeline_failed",
            "message": f"Generation finished with {len(failed)} failed agent(s): {', '.join(failed)}. "
                       "Check the backend server logs.",
        })
    else:
        await emit({"type": "pipeline_complete"})
    return states


async def _run_prototype_agent(
    context: str, definition, emit: EmitFn, agent_id: str, llm_gate: asyncio.Semaphore,
) -> str:
    """
    Tries Stitch first (real design tool, proper UI). Falls back to the
    original small-LLM raw-HTML generation if Stitch isn't configured or
    the call fails — the pipeline never hard-fails because of Stitch.

    `llm_gate` serialises the LLM fallback with the rest of the pipeline's
    provider calls; the Stitch call sits outside it, because Stitch is a
    separate service, not the shared free-tier token budget.
    """
    stitch_html = await stitch_service.generate_prototype_html(context)
    if stitch_html:
        await emit({"type": "agent_log", "agent": agent_id, "message": "Generated via Google Stitch."})
        return stitch_html

    await emit({"type": "agent_log", "agent": agent_id, "message": "Stitch unavailable — falling back to LLM-generated HTML."})
    async with llm_gate:
        result = await llm_router.chat(
            messages=[
                {"role": "system", "content": definition.system_prompt},
                {"role": "user", "content": context},
            ],
            max_tokens=definition.max_tokens,
            temperature=0.3,
            max_rate_limit_wait=settings.llm_generation_max_rate_limit_wait,
        )
    html = _strip_markdown_fences(result.text.strip())
    # Same click-safety-net Stitch screens get — guarantees no dead button
    # even if the model forgot to wire something up.
    if "</body>" in html:
        html = html.replace("</body>", stitch_service._CLICK_SAFETY_NET_SCRIPT + "</body>", 1)
    else:
        html += stitch_service._CLICK_SAFETY_NET_SCRIPT
    return html