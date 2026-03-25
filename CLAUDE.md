# Life Scouter
AI-powered life coaching platform with multi-agent architecture.
## Tech Stack
- **Backend**: Python 3.11, FastAPI, LangGraph, Uvicorn (port 8001)
- **Frontend**: Next.js 16 (App Router), shadcn/ui, Zustand, framer-motion (port 3000)
- **LLM**: OpenAI-compatible via LangChain (GPT-4o default)
- **Tools**: Tavily Search, BeautifulSoup4, WeasyPrint, python-docx
## Architecture
Two-tier decoupled system. See `docs/architecture.md` for full spec.
- `api/` — FastAPI REST + WebSocket endpoints
- `agents/` — LangGraph agent nodes (career/, life/, learning/, onboarding/, settings/)
- `orchestrator/` — Graph definition, state, supervisors, checkpointing
- `context/` — Profile, artifact, task, goal, memory managers
- `tools/` — Tavily search, job/course search, web scraper, doc generation
- `models/` — Pydantic schemas (UserProfile, Task, Goal, Artifact)
- `services/` — APScheduler background jobs
- `frontend/` — Next.js app with chat UI, dashboard, onboarding modal
## Key Concepts
- **AgentState** (`orchestrator/state.py`): Shared TypedDict passed through all nodes
  - `messages`, `active_agent`, `task_id`, `budget_stats`, `next`
- **Two execution modes**: Pure-prompt (single LLM call) vs ReAct (tool-calling loop)
- **Every agent** gets injected context: user profile + last 3 artifacts from its group
- **Supervisors** route to sub-agents via `with_structured_output`
## Commands
```bash
# Backend
uvicorn api.main:app --reload --port 8001
# Frontend
cd frontend && npm run dev
# Tests
pytest tests/ -v
cd frontend && npm test
# Type checking
cd frontend && npx tsc --noEmit
mypy api/ agents/ orchestrator/ --ignore-missing-imports
# Docker
docker compose up --build
```
## Code Style
- Python: Black formatter, isort, type hints on all public functions
- TypeScript: ESLint + Prettier, functional components, prefer server components
- Agents: Always define system prompt as a constant, never inline
- Tools: All @tool functions must have docstrings with Args/Returns
- State: Never mutate AgentState directly — return new values
## Important Files
- `orchestrator/graph.py` — Root graph definition (touch with extreme care)
- `orchestrator/state.py` — AgentState TypedDict (breaking changes cascade everywhere)
- `context/profile_manager.py` — All agents depend on this
- `api/routes/chat.py` — WebSocket handler, the main interaction path
- `frontend/stores/` — Zustand stores (source of truth for UI state)
## Rules
- Never add new agents without updating `orchestrator/graph.py` routing
- All artifacts go through `tools/save_artifact.py` — never write to data/ directly
- WebSocket messages follow the protocol: status → ai_message → done | error
- Keep agent system prompts < 2000 tokens to preserve context for conversation
- LinkedIn scraping is blocked — always route through Tavily proxy
## Deeper Docs (read when relevant)
- `docs/architecture.md` — Full agent architecture spec
- `docs/agent-patterns.md` — How to add new agents
- `docs/api-protocol.md` — WebSocket message format
- `docs/tools-guide.md` — Tool implementation patterns
