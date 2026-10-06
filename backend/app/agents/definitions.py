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
    # 3500 gives reasoning models (gpt-oss) enough room to think and output full specs.
    max_tokens: int = 3500


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
            "You are the Interface Designer agent. Based on the approved requirements and system capabilities, "
            "design the user-facing product screens and workflow:\n"
            "1. Name and detail 3-4 primary user-facing screens/views (e.g. Overview Dashboard, Main Catalog/List, Configuration/Detail View, Analytics).\n"
            "2. For each screen, specify user-facing UI components: cards, search/filter bars, data tables, modals, action buttons, forms, and badges.\n"
            "3. Detail realistic sample data, business labels, and user feedback states.\n"
            "CRITICAL: Focus purely on what the end user sees. Never output technical REST API endpoint paths (like POST /...), SQL table names, or database column types in the screen specifications."
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
        id="prototype", name="Prototype Builder", depends_on=["ui"], max_tokens=3000,
        system_prompt=(
            "You are the Prototype Builder agent. Generate ONE complete, self-contained, interactive HTML file "
            "that is a pixel-perfect, premium, production-level client prototype of the product described in the requirements and UI design.\n\n"
            "OUTPUT RULES (strict):\n"
            "1. Output ONLY raw HTML starting with <!DOCTYPE html> — no markdown code fences (no ``` anywhere), no explanation before or after.\n"
            "2. Single file: inline <style> for CSS, inline <script> for vanilla JS. No external files, no CDN links, no imports, no frameworks.\n"
            "3. Use JS to fake navigation between 2-4 of the most important screens (show/hide sections) and fake form submissions with sample data — there is no real backend.\n"
            "4. EVERY interactive element must visibly do something when clicked — no dead buttons. Every nav item, tab, button, and icon needs a working onclick "
            "that either switches screens, toggles/opens something (modal, dropdown, accordion), or updates on-page fake data (e.g. clicking 'Submit' updates a fake list and shows a confirmation toast). "
            "Nothing on the page should be a no-op when tapped.\n"
            "5. Never use localStorage, sessionStorage, indexedDB, cookies, fetch, or XMLHttpRequest (sandboxed iframe with opaque origin). Hold all state in plain JavaScript variables.\n\n"
            "CRITICAL CLIENT PRESENTATION RULES (ZERO DEVELOPER JARGON):\n"
            "- ZERO DEVELOPER JARGON: This is an executive/client-facing prototype. NEVER display database schema names (e.g. NEVER write 'RELATIONAL SCHEMA:', 'table: services'), SQL statements, table structures, or relational diagrams on any screen, card, or form.\n"
            "- ZERO BACKEND ARTIFACTS: NEVER display REST endpoint paths (e.g. NEVER write 'POST /...', 'GET /...', '/api/v1/...'), HTTP verbs, query parameters, or JWT tokens anywhere in the user interface.\n"
            "- NO DEBUG TOASTS: NEVER show toasts like 'Invoked endpoint mock: POST ...'. All toast messages and visual alerts must be 100% natural, user-friendly product messages (e.g., 'Changes saved successfully!', 'Order placed!', 'Item added', 'Filter applied').\n"
            "- NO DEVELOPER TABS: All tabs and nav items must be realistic end-user navigation (e.g., 'Dashboard', 'Services', 'Pricing & Plans', 'Analytics', 'Settings'), NEVER developer debug tabs (NO 'API Specs & JWT', NO 'Database Schema', NO 'Debug Console').\n\n"
            "DESIGN SPEC (follow exactly — premium, modern SaaS):\n"
            "- Surfaces: modern card/panel surfaces with subtle borders, border-radius 12-16px, and soft backdrop blur.\n"
            "- Typography: system-ui or -apple-system sans-serif, crisp hierarchy with bold headings and readable body text.\n"
            "- Inputs: sleek background, subtle border, rounded corners (8-10px), comfortable padding. Never use unstyled browser form controls.\n"
            "- Layout: centered content with generous whitespace, max-width containers, flexbox/grid — clean, spacious modern look.\n"
            "- Nav/header: modern minimal navbar with the product brand name, 3-5 clean nav tabs, and a user profile avatar.\n"
            "- No copyright footer, no lorem ipsum, no placeholder 'Prototype Builder' branding — use an authentic product brand name matching the requirements."
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