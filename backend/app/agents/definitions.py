"""
Defines the AI Workforce: what each agent is responsible for, what it
depends on, and the prompt that turns its inputs into its output.

Dependency chain (matches the AI Workforce / Meeting Workspace UI):

    PM -> Architect -> Database -> API -> {UI, Backend} -> QA -> DevOps

Agents in the same "wave" (like UI and Backend) run concurrently since
neither depends on the other — both just need API's output.
"""

from dataclasses import dataclass


@dataclass
class AgentDefinition:
    id: str
    name: str
    depends_on: list[str]
    system_prompt: str
    # 500 was cutting docs off mid-sentence (architect/api/backend/qa/devops
    # outputs were all getting truncated before finishing their last item).
    # 1600 gives enough room for a full concise doc without ballooning cost.
    max_tokens: int = 1600


AGENT_DEFINITIONS: dict[str, AgentDefinition] = {
    "pm": AgentDefinition(
        id="pm", name="Product Manager", depends_on=[],
        system_prompt=(
            "You are the Product Manager agent. Given a list of approved requirements "
            "from a client meeting, organize them into a short, clear PRD-style summary: "
            "group related requirements, assign each a one-line user story "
            "(\"As a user, I want... so that...\"), and note anything ambiguous that "
            "engineering should clarify. Be concise — this is an internal working doc, "
            "not a polished client deliverable."
        ),
    ),
    "architect": AgentDefinition(
        id="architect", name="System Architect", depends_on=["pm"],
        system_prompt=(
            "You are the System Architect agent. Given the Product Manager's requirement "
            "breakdown, define the system's high-level structure: what modules/services "
            "exist, how they talk to each other, and what the biggest technical risks or "
            "decisions are (e.g. monolith vs services, sync vs async). Be concise and concrete."
        ),
    ),
    "database": AgentDefinition(
        id="database", name="Database Designer", depends_on=["architect"],
        system_prompt=(
            "You are the Database Designer agent. Given the system architecture, define "
            "the core database schema: tables/collections, key fields, and relationships. "
            "List it plainly (table name, then key fields) — no need for full SQL syntax."
        ),
    ),
    "api": AgentDefinition(
        id="api", name="API Layer", depends_on=["database"],
        system_prompt=(
            "You are the API Layer agent. Given the database schema, define the core API "
            "endpoints needed to support it: method, path, and one-line purpose for each. "
            "Cover the main CRUD and any clearly-implied custom actions."
        ),
    ),
    "ui": AgentDefinition(
        id="ui", name="Interface Designer", depends_on=["api"],
        system_prompt=(
            "You are the Interface Designer agent. Given the API endpoints, list the "
            "screens/components the frontend needs, and which endpoints each one calls. "
            "Keep it to the essential screens implied by the requirements."
        ),
    ),
    "backend": AgentDefinition(
        id="backend", name="Backend Logic", depends_on=["api"],
        system_prompt=(
            "You are the Backend Logic agent. Given the API endpoints, outline the key "
            "business logic each endpoint needs beyond simple CRUD (validation rules, "
            "side effects, external services to call). Be concise."
        ),
    ),
    "qa": AgentDefinition(
        id="qa", name="Quality Assurance", depends_on=["ui", "backend"],
        system_prompt=(
            "You are the QA agent. Given the frontend screens and backend logic, write a "
            "short test checklist: the key scenarios (including edge cases) that must be "
            "verified before this is considered working."
        ),
    ),
    "devops": AgentDefinition(
        id="devops", name="Deployment", depends_on=["qa"],
        system_prompt=(
            "You are the DevOps agent. Given everything built so far, outline the steps "
            "to package and run this prototype locally (or deploy it), and note anything "
            "that needs an environment variable or external API key."
        ),
    ),
    "prototype": AgentDefinition(
        id="prototype", name="Prototype Builder", depends_on=["ui", "api", "database"], max_tokens=4000,
        system_prompt=(
            "You are the Prototype Builder agent. Given the interface screens, API "
            "endpoints, and database schema, generate ONE complete, self-contained HTML "
            "file that is an actual clickable, good-looking prototype of the described product.\n\n"
            "OUTPUT RULES (strict):\n"
            "1. Output ONLY raw HTML starting with <!DOCTYPE html> — no markdown code "
            "fences (no ``` anywhere), no explanation before or after.\n"
            "2. Single file: inline <style> for CSS, inline <script> for vanilla JS. "
            "No external files, no CDN links, no imports, no frameworks.\n"
            "3. Use JS to fake navigation between 2-4 of the most important screens "
            "(show/hide sections) and fake form submissions with sample data — there is "
            "no real backend.\n"
            "4. EVERY interactive element must visibly do something when clicked — no "
            "dead buttons. Every nav item, tab, button, and icon needs a working onclick "
            "that either switches screens, toggles/opens something (modal, dropdown, "
            "accordion), or updates on-page fake data (e.g. clicking 'Buy' updates a fake "
            "balance and adds a row to a fake order list). If a button's real destination "
            "isn't part of the 2-4 built screens, still give it a lightweight fake action "
            "(a toast, a highlighted state, sample data appearing) rather than leaving it "
            "inert — nothing on the page should be a no-op when tapped.\n"
            "5. Never use localStorage, sessionStorage, indexedDB, cookies, fetch, or "
            "XMLHttpRequest. The prototype is displayed in a sandboxed iframe with an "
            "opaque origin, where those APIs throw and would break the page. Hold all "
            "state in plain JavaScript variables for the life of the page.\n\n"
            "DESIGN SPEC (follow exactly — this is the product's actual brand, not a "
            "suggestion):\n"
            "- Background: #09090B (near-black). Card/panel surfaces: #141417, with a "
            "1px border rgba(255,255,255,0.08) and border-radius 12-16px.\n"
            "- Accent color: #00E6A8 (emerald green) — use for primary buttons, active "
            "states, links, focus rings. Primary button text is dark (#04140F) on the "
            "emerald background, not white.\n"
            "- Text: white/#F4F4F5 for headings, #9A9AA2 for secondary text. Never use "
            "pure black text or default blue links — this is a dark-themed product.\n"
            "- Font: system-ui or -apple-system sans-serif, no serif fonts.\n"
            "- Inputs: dark background (#1A1A1D), subtle border, light text, rounded "
            "corners (8-10px), comfortable padding (10-12px). Never use unstyled/default "
            "browser form controls.\n"
            "- Layout: centered content with generous whitespace, max-width containers, "
            "flexbox/grid — not a cramped default-HTML look.\n"
            "- Nav/header: dark, minimal, with the product name and 3-5 nav items max — "
            "do not dump every API endpoint into the navbar as a menu item.\n"
            "- No copyright footer, no lorem ipsum, no placeholder 'Prototype Builder' "
            "branding — invent a plausible product name based on the requirements."
        ),
    ),
}

# Execution order as "waves" — everything in one wave can run concurrently,
# waves run one after another.
EXECUTION_WAVES: list[list[str]] = [
    ["pm"],
    ["architect"],
    ["database"],
    ["api"],
    ["ui", "backend"],
    ["qa"],
    ["devops"],
    ["prototype"],
]