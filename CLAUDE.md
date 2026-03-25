# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Life Scouter
AI-powered life coaching platform with multi-agent architecture.

## Tech Stack
- **Backend**: Python 3.11, FastAPI, LangGraph, Uvicorn (port 8000 — see `api/main.py` docstring)
- **Frontend**: Next.js (App Router), shadcn/ui, Zustand, framer-motion (port 3000)
- **LLM**: Google Gemini via `langchain_google_genai` (`ChatGoogleGenerativeAI`)
  - `model_supervisors` / `model_orchestrator` / `model_onboarding` / `model_settings`: `gemini-3-flash-preview`
  - `model_low_complexity` / `model_high_complexity`: `gemini-3.1-pro-preview`
- **Tools**: Tavily Search (`tools/search.py`), BeautifulSoup4 (`tools/web_scraper.py`), WeasyPrint/python-docx (`tools/document_generator.py`)
- **Storage**: JSON files under `data/` (profile, artifacts, memory); SQLite LangGraph checkpoints at `data/checkpoints/`

## Commands
```bash
# Backend (port 8000, not 8001)
uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Tests (manual runner — not pytest-discovered; run directly)
python tests/test_orchestrator.py
python tests/test_career.py
python tests/test_life.py
python tests/test_learning.py

# Docker
docker compose up --build
```

> **Tests are not pytest-compatible.** Each file defines `run_tests()` with a `if __name__ == "__main__"` guard. `pytest tests/ -v` will not discover them.

## Architecture

### Execution Flow
```
WebSocket /api/chat/{thread_id}
  → router_node (initializes budget_stats)
  → route_to_group() reads state["active_agent"]
  → career_branch | life_branch | learning_branch | onboarding_agent | settings_agent
  → END
```

### Two-tier LangGraph supervisor hierarchy

**Top level** (`orchestrator/graph.py`):
- `router_node`: initializes `budget_stats` if absent
- `route_to_group()`: dispatches on `state["active_agent"]` — values: `"career"`, `"life"`, `"learning"`, `"onboarding"`, `"settings"`
- Unrecognized `active_agent` silently routes to END

**Branch level** (career / life / learning):
- Each is a compiled `StateGraph` with: `START → supervisor → conditional_edges → sub-agent → supervisor → ...`
- Sub-agents always edge back to supervisor; supervisor decides `__end__` or next sub-agent
- Termination heuristic in `route_next()`: content-sniffing for `"[SYSTEM]"`, `"Generated"`, `"Saved artifact"` in last AIMessage — fragile, do not rely on it in new agents

**Supervisor routing**:
- Career uses a hand-written supervisor (`agents/career/supervisor.py`) with a `Route` Pydantic model and `with_structured_output`
- Life and learning use the generic factory `orchestrator/supervisor.py:create_supervisor()` with a `RouteParams` model
- Both enforce budget via `orchestrator/supervisor.py:enforce_budget()` (MAX_ITERATIONS=5, MAX_TOOL_CALLS=15, MAX_EXECUTION_TIME_SEC=300)

**Agent execution modes**:
- **Pure-prompt**: single `llm.invoke()` call, no tools (e.g. `goals.py`, `habits.py`, `health.py`, `therapy.py`, `course_rec.py`, `progress.py`)
- **ReAct**: `create_react_agent(llm, tools)` with tool-calling loop (e.g. `resume.py`, `job_search.py`, `interview_prep.py`, `career_planning.py`, `study_plan.py`)
- **Tool-bound**: `llm.bind_tools([...])` with manual tool call dispatch (e.g. `onboarding/agent.py`)

**Context injection** (every agent node does this):
```python
profile = ProfileManager().load()         # data/user_profile.json
artifacts = ArtifactLoader.load_recent("career")  # last 3 .md/.txt files by mtime
memory = MemoryDistiller.load_summary()   # data/memory/context_store.json
```

**Memory distillation**: After each WebSocket response, `chat.py` fires `MemoryDistiller.distill()` in a thread executor (non-fatal — exceptions are swallowed). Extracts facts into 5 categories: `career_insights`, `life_insights`, `learning_insights`, `cross_domain_goals`, `action_items`.

**Artifact persistence**: Agents write files directly via `open()` to `data/{group}/artifacts/{name}_{task_id}.md`. There is **no** `tools/save_artifact.py` — each agent handles its own file I/O.

**Checkpointing**: `orchestrator/checkpoint.py` provides a singleton `SqliteSaver`. `chat.py` passes `{"configurable": {"thread_id": thread_id}}` directly — it does **not** use `get_checkpoint_config()`, so threads are not namespaced by agent group.

## AgentState (`orchestrator/state.py`)
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], _add_messages]  # append-only reducer
    active_agent: str    # "career" | "life" | "learning" | "onboarding" | "settings"
    task_id: str         # UUID or "interactive_session"
    budget_stats: BudgetStats  # {iterations, tool_calls, start_time}
    next: str            # routing flag read by branch conditional_edges
```
Never mutate directly — return new values from node functions.

## Key Files
- `orchestrator/graph.py` — entire graph topology; all branch wiring lives here
- `orchestrator/state.py` — AgentState TypedDict; cascading breakage if changed
- `orchestrator/supervisor.py` — `enforce_budget()` + generic `create_supervisor()` factory
- `agents/career/supervisor.py` — hand-written career supervisor (does not use the factory)
- `context/profile_manager.py` — reads/writes `data/user_profile.json`
- `context/artifact_loader.py` — loads recent artifacts by mtime for context injection
- `context/memory_distiller.py` — post-conversation fact extraction and cross-domain store
- `api/routes/chat.py` — WebSocket handler; the main interaction path
- `config/settings.py` — all model names and file paths; read from env / `.env`
- `frontend/src/store/useAppStore.ts` — single Zustand store; source of truth for UI state

## WebSocket Protocol
Client sends:
```json
{"message": "...", "active_agent": "career|life|learning|onboarding|settings"}
```
Server streams in order:
```json
{"type": "status", "content": "processing"}
{"type": "ai_message", "content": "...", "agent_name": "..."}
{"type": "done"}
// or on error:
{"type": "error", "content": "..."}
```

## Rules
- Never add new agents without wiring them into `orchestrator/graph.py`
- New domain agents must also add a supervisor and branch function in `graph.py`
- System prompts must be module-level constants, never inline strings
- `@tool` functions require docstrings with `Args:` and `Returns:` sections
- LinkedIn direct scraping is blocked — use Tavily search as a proxy
- Keep agent system prompts under ~2000 tokens (context budget for conversation history)
- The career supervisor is a separate implementation from the generic factory — keep them in sync if changing budget/routing logic

## Known Fragilities
- `route_next()` in each branch terminates on content-sniffing (`"Generated"`, `"Saved artifact"`, `"[SYSTEM]"`) — user messages containing these strings can trigger early exit
- `sendMessage` in the frontend reconnects via `setTimeout(500ms)` — messages sent while reconnecting are silently dropped
- `orchestrator_graph.invoke()` runs synchronously in `run_in_executor` — high concurrency will exhaust the default thread pool
- `MemoryDistiller.distill()` errors are fully suppressed; a corrupted store silently stops all distillation
