# Life Scout

## Overview
Life Scout is an AI-powered personal assistant built on LangGraph, featuring a decoupled Next.js frontend and FastAPI backend with a two-level supervisor architecture.

Three domain agent groups — **Career**, **Life**, and **Learning** — each managed by a supervisor that routes user requests to specialized sub-agents. Agents use Google Gemini via LangChain, with Tavily search and web scraping as external tools.

## Architecture

```
WebSocket /api/chat/{thread_id}
  → router_node (budget init)
  → route_to_group()
  → career_branch | life_branch | learning_branch | onboarding | settings
      └─ supervisor → sub-agent → supervisor → ... → END
  → END
```

- **Orchestrator**: top-level LangGraph `StateGraph` dispatching to compiled sub-graphs
- **Supervisors**: `create_supervisor()` factory handles budget enforcement, concurrency guards, memory injection, and LLM routing for all three domain branches
- **Agents**: pure-prompt (single `llm.invoke`) or ReAct (`create_react_agent` with tool loop)
- **Context injection**: every agent receives user profile, recent artifacts, and cross-domain memory
- **Checkpointing**: SQLite via `langgraph-checkpoint-sqlite`, namespaced by `{agent_group}_{thread_id}`

## Setup Instructions

### Environment Setup
1. Copy `.env.example` to `.env`
2. Fill in your API keys:
   - `GEMINI_API_KEY` (required) — Google Gemini
   - `TAVILY_API_KEY` (required for search) — Tavily web search
   - `LANGSMITH_API_KEY` (optional) — enables LangSmith tracing
   - `LANGSMITH_PROJECT` (optional, defaults to `lifescouter`)

### Running with Docker (Recommended)
```bash
docker-compose up --build
```
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000` (API docs at `/docs`)

### Local Development

**1. Backend (FastAPI)**
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Frontend (Next.js)**
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# All unit tests (no API keys needed)
pytest tests/ -v -m "not integration"

# Integration tests (require GEMINI_API_KEY and/or TAVILY_API_KEY)
pytest tests/ -v -m integration
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| WS | `/api/chat/{thread_id}` | Bidirectional chat (send message, stream responses) |
| GET | `/api/profile` | Get user profile |
| PUT | `/api/profile` | Update user profile |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/artifacts` | List all artifacts |
| GET | `/api/costs` | Token usage across all sessions |
| GET | `/api/costs/{thread_id}` | Token usage for a specific session |
| GET | `/health` | Health check |

## Observability

**LangSmith tracing** is enabled automatically when `LANGSMITH_API_KEY` is set. Every LLM call, tool execution, and supervisor routing decision is traced with no per-file changes needed.

**Cost tracking** accumulates token usage per agent per session in-memory and exposes it via the `/api/costs` endpoint. The `CostCallbackHandler` is injected into every graph invocation through LangChain's callback system.

## Project Structure

```
api/                    FastAPI routes and WebSocket handler
agents/
  career/               6 sub-agents + supervisor
  life/                 4 sub-agents + supervisor
  learning/             3 sub-agents + supervisor
  onboarding/           Profile setup agent
  settings/             Profile update agent
orchestrator/
  graph.py              Full graph topology
  supervisor.py         Generic supervisor factory + budget enforcement
  state.py              AgentState TypedDict
  checkpoint.py         SQLite checkpointer singleton
observability/
  tracing.py            LangSmith env-var configuration
  cost_tracker.py       Token usage callback + accumulator
context/                Profile, artifact, and memory managers
tools/                  Search, scraping, document gen, artifact writer
config/                 Settings (Pydantic BaseSettings)
frontend/               Next.js App Router + shadcn/ui
tests/                  pytest suite (40 unit + 20 integration tests)
docs/                   Architecture and execution trace docs
```
