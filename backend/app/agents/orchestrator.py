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
from app.llm.router import llm_router
from app.services import stitch_service

logger = logging.getLogger("protopilot.agents")

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
                state.output = await _run_prototype_agent(context, definition, emit, agent_id)
            else:
                result = await llm_router.chat(
                    messages=[
                        {"role": "system", "content": definition.system_prompt},
                        {"role": "user", "content": context},
                    ],
                    max_tokens=definition.max_tokens,
                    temperature=0.3,
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
        except RuntimeError as e:
            logger.warning("agent %s failed: %s", agent_id, e)
            state.status = AgentStatus.FAILED
            state.progress = 0
            state.logs.append(f"Failed: {e}")
            await emit({"type": "agent_update", **state.to_event_dict()})
            await emit({"type": "agent_log", "agent": agent_id, "message": state.logs[-1]})

    for wave in EXECUTION_WAVES:
        await asyncio.gather(*(run_one(agent_id) for agent_id in wave))

    await emit({"type": "pipeline_complete"})
    return states


async def _run_prototype_agent(context: str, definition, emit: EmitFn, agent_id: str) -> str:
    """
    Tries Stitch first (real design tool, proper UI). Falls back to the
    original small-LLM raw-HTML generation if Stitch isn't configured or
    the call fails — the pipeline never hard-fails because of Stitch.
    """
    stitch_html = await stitch_service.generate_prototype_html(context)
    if stitch_html:
        await emit({"type": "agent_log", "agent": agent_id, "message": "Generated via Google Stitch."})
        return stitch_html

    await emit({"type": "agent_log", "agent": agent_id, "message": "Stitch unavailable — falling back to LLM-generated HTML."})
    result = await llm_router.chat(
        messages=[
            {"role": "system", "content": definition.system_prompt},
            {"role": "user", "content": context},
        ],
        max_tokens=definition.max_tokens,
        temperature=0.3,
    )
    html = _strip_markdown_fences(result.text.strip())
    # Same click-safety-net Stitch screens get — guarantees no dead button
    # even if the model forgot to wire something up.
    if "</body>" in html:
        html = html.replace("</body>", stitch_service._CLICK_SAFETY_NET_SCRIPT + "</body>", 1)
    else:
        html += stitch_service._CLICK_SAFETY_NET_SCRIPT
    return html