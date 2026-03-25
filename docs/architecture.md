# Architecture Spec

## System Overview

Two-tier decoupled architecture: Next.js 16 frontend (port 3000) ↔ FastAPI backend (port 8001) communicating via REST + WebSocket.

Backend uses LangGraph for multi-agent orchestration with a two-level supervisor pattern.

## Execution Flow

```
Client WebSocket → /api/chat/{thread_id}
  → chat.py handler
    → orchestrator_graph.invoke(state, config)
      → router_node (init budget_stats)
        → route_to_group() conditional edge
          ├── career_branch (compiled sub-graph)
          ├── life_branch (compiled sub-graph)
          ├── learning_branch (compiled sub-graph)
          ├── onboarding_agent (leaf node)
          └── settings_agent (leaf node)
    → extract new AI messages from result
    → async MemoryDistiller.distill()
    → stream responses back via WebSocket
```

## Graph Construction (`orchestrator/graph.py`)

**Root Graph: `StateGraph(AgentState)`**

Nodes:
- `router` → `router_node()` — initializes `budget_stats` if missing
- `career_branch` → compiled sub-graph from `create_career_branch()`
- `life_branch` → compiled sub-graph from `create_life_branch()`
- `learning_branch` → compiled sub-graph from `create_learning_branch()`
- `onboarding_agent` → `onboarding_agent_node()`
- `settings_agent` → `settings_agent_node()`

Edges:
```
START → router
router → conditional(route_to_group)
  "career" → career_branch → END
  "life" → life_branch → END
  "learning" → learning_branch → END
  "onboarding" → onboarding_agent → END
  "settings" → settings_agent → END
  default → END
```

Routing function reads `state["active_agent"].lower()`.

## Sub-Graph Pattern (Domain Branches)

Each domain branch follows an identical supervisor-loop pattern:

```
START → supervisor
supervisor → conditional(route_next)
  "{agent_name}" → agent_node → supervisor (cycle)
  "__end__" → END
```

All sub-agents route back to supervisor. Supervisor decides next agent or `__end__`.

### Career Branch
Supervisor → `resume_agent`, `job_search_agent`, `interview_prep_agent`, `career_planning_agent`, `linkedin_agent`, `lead_generation_agent`

### Life Branch
Supervisor → `goals_agent`, `habits_agent`, `health_agent`, `therapy_agent`

### Learning Branch
Supervisor → `study_plan_agent`, `course_rec_agent`, `progress_agent`

## State Schema (`orchestrator/state.py`)

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], _add_messages]  # Custom reducer: concatenation
    active_agent: str          # "career"|"life"|"learning"|"onboarding"|"settings"
    task_id: str               # UUID of active Task
    budget_stats: BudgetStats  # {iterations: int, tool_calls: int, start_time: float}
    next: str                  # Routing flag: node name or "__end__"
```

## Budget Enforcement (`orchestrator/supervisor.py`)

Hard limits checked at supervisor entry before routing:
```
MAX_ITERATIONS = 5
MAX_TOOL_CALLS = 15
MAX_EXECUTION_TIME_SEC = 300
```

On breach: returns `AIMessage` with `content="[SYSTEM] Budget Exceeded..."` and `additional_kwargs["force_end"] = True`. Conditional router checks for this signal.

## Checkpointing

- `SqliteSaver` from `langgraph.checkpoint.sqlite`
- DB path: `{settings.checkpoints_dir}/overall_thread.db`
- Thread ID format: `"{agent_group}_{thread_id}"`

## Supervisor Routing

All supervisors use `with_structured_output` on `ChatGoogleGenerativeAI(temperature=0.0)`:

```python
class Route(BaseModel):
    next: Literal["agent_a", "agent_b", ..., "__end__"]
    conversational_response: str | None = None
```

Supervisor flow:
1. `enforce_budget(state)` — check limits
2. Load `MemoryDistiller.load_summary()` — cross-domain context
3. Construct `[SystemMessage(PROMPT + memory)] + state.messages`
4. Invoke `llm.with_structured_output(Route)`
5. If `next == "__end__"` and `task_id` exists → mark task completed
6. Increment `stats["iterations"]`
7. Return `{budget_stats, next, messages}`

## Context Injection

Every agent receives three injected context sources in its system prompt:

```python
profile = ProfileManager().load()                    # User profile JSON
artifacts = ArtifactLoader.load_recent("{domain}")    # Last 3 artifacts from domain
memory = MemoryDistiller.load_summary()               # Cross-domain distilled memory

sys_content = f"{SYSTEM_PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}"
```

## Model Selection

Configured in `config/settings.py`:
- `model_supervisors` — gemini-3-flash-preview (deterministic routing)
- `model_high_complexity` — gemini-3.1-pro-preview (resume, interview, therapy, career planning)
- `model_low_complexity` — gemini-3.1-pro-preview (goals, habits, health, study plan, progress)
- `model_onboarding` — gemini-3-flash-preview
- `model_settings` — gemini-3-flash-preview

## Data Storage

File-based JSON storage under `data/`:

```
data/
├── user_profile.json
├── notifications.json
├── memory/context_store.json          # MemoryDistiller output
├── cache/scraper/{url_hash}.json      # Web scraper cache (24h TTL)
├── checkpoints/                       # LangGraph SQLite
├── {career,life,learning}/
│   ├── artifacts/
│   │   ├── index.json                 # ArtifactManager registry
│   │   └── {artifact_files}
│   ├── logs/{task_id}.json            # TaskManager logs
│   ├── conversations/{session_id}.json
│   └── goals/goals.json
```

## Frontend Architecture

- Next.js 16 App Router, client-side rendered, standalone output
- Single Zustand store (`useAppStore`) manages all state
- WebSocket per agent session (threadId = `{agent}-session`)
- REST for profile, tasks, artifacts, notifications
- shadcn/ui components, Tailwind CSS 4, framer-motion animations
- Dark mode only (oklch color scheme)
- API_BASE defaults to `http://localhost:8001`

### Component Hierarchy
```
layout.tsx (Inter font, dark mode)
└── page.tsx
    ├── Sidebar (agent switcher, notifications)
    ├── Header (agent label, dashboard toggle)
    ├── ChatWindow (messages + typing indicator)
    ├── DashboardDrawer (tasks + artifacts)
    └── OnboardingModal (full-screen, chatwindow with agentOverride="onboarding")
```

## Background Services

`services/scheduler.py` — `ProactiveScheduler` using `AsyncIOScheduler`:
- `daily_career_scan` — 24h interval, checks career goals in memory, creates notifications
- `daily_habit_nudge` — 24h interval, checks health/habit goals, creates notifications
