# Execution Trace: "find me remote Python jobs"

Complete call trace from WebSocket frame to final response, covering every
function call, state mutation, and tool invocation in order.

---

## Phase 0 — Frontend (TypeScript)

**`frontend/src/store/useAppStore.ts` → `sendMessage()`**

1. Builds payload: `{ message: "find me remote Python jobs", active_agent: "career" }`
2. If `ws.readyState === WebSocket.OPEN`: sends immediately via `ws.send(JSON.stringify(payload))`
3. Else: pushes to `pendingQueue`, calls `connectWs(threadId)` which opens
   `ws://localhost:8000/api/chat/{threadId}` — on `socket.onopen`, drains `pendingQueue`

---

## Phase 1 — WebSocket handler

**`api/routes/chat.py` → `websocket_chat()`**

| Step | Code | What happens | State mutation |
|------|------|--------------|----------------|
| 1 | `:52` | `manager.connect(websocket, thread_id)` → `websocket.accept()`, adds socket to `ConnectionManager.active_connections[thread_id]` | Server-side connection registry |
| 2 | `:56` | `await websocket.receive_json()` → blocks until client sends JSON | — |
| 3 | `:57–58` | Destructure: `user_message = "find me remote Python jobs"`, `active_agent = "career"` | — |
| 4 | `:65` | Send to client: `{"type": "status", "content": "processing"}` | — |
| 5 | `:68` | `config = get_checkpoint_config("career", thread_id)` | — |

**`orchestrator/checkpoint.py` → `get_checkpoint_config()`**
- Returns `{"configurable": {"thread_id": "career_{thread_id}"}}` — namespaced to prevent
  cross-group checkpoint collisions

| Step | Code | What happens |
|------|------|--------------|
| 6 | `:69` | `input_messages = [HumanMessage(content="find me remote Python jobs")]` |
| 7 | `:72–76` | Build initial state dict |
| 8 | `:80–83` | `loop.run_in_executor(None, lambda: orchestrator_graph.invoke(state, config=config))` — blocks the async handler, runs synchronous LangGraph execution in the default thread-pool executor |

Initial state:
```python
{
    "messages": [HumanMessage(content="find me remote Python jobs")],
    "active_agent": "career",
    "task_id": "interactive_session",
}
```

---

## Phase 2 — Top-level orchestrator graph

The compiled `orchestrator_graph` (`orchestrator/graph.py:274`) has topology:

```
START → router → conditional_edges(route_to_group) → career_branch → END
```

### Node 1: `router_node()`

- Reads `state["budget_stats"]` — absent on first call, so `stats = {}`
- Always resets `start_time` to `time.time()` (budget timing is per-request, not cumulative)
- Preserves any `iterations`/`tool_calls` already in state

**State mutation returned:**
```python
{"budget_stats": {"iterations": 0, "tool_calls": 0, "start_time": 1742911200.0}}
```

### Conditional edge: `route_to_group()`

- Reads `state["active_agent"]` → `"career"`
- Matches `CAREER_GROUP` → returns `"career_branch"`

### Node 2: `career_branch` (compiled sub-graph)

Career branch topology:
```
START → supervisor → conditional_edges(route_next) → job_search_agent → supervisor → conditional_edges(route_next) → END
```

---

## Phase 3 — Career branch, cycle 1: supervisor routes to job_search_agent

### Sub-node: `supervisor` → `career_supervisor_node` closure

**`orchestrator/supervisor.py` → `supervisor_node()`**

| Line | Action | Detail |
|------|--------|--------|
| `:102` | `stats = state.get("budget_stats", ...)` | `{"iterations": 0, "tool_calls": 0, "start_time": ...}` |
| `:103` | `task_id = state.get("task_id")` | `"interactive_session"` |
| `:106` | `enforce_budget(state)` | `iterations(0) < 5`, `tool_calls(0) < 15`, `elapsed < 300` → returns `{}` (no breach) |
| `:125` | Task-status check | `task_manager.get_task("interactive_session")` → `None` (interactive sessions are not registered tasks) → skip |
| `:143` | `stats["iterations"] += 1` | **iterations now 1** |
| `:146` | `MemoryDistiller.load_summary()` | Reads `data/memory/context_store.json` → returns formatted facts or `"(No persistent memory facts extracted yet.)"` |
| `:147` | Build `SystemMessage` | `CAREER_PROMPT + "\n\nCross-Domain Context:\n" + memory` |
| `:148` | `formatted_messages` | `[SystemMessage(...)] + [HumanMessage("find me remote Python jobs")]` |
| `:151` | **LLM CALL #1** | `gemini-3-flash-preview` via `with_structured_output(RouteParams)` → `RouteParams(next="job_search_agent", conversational_response=None)` |
| `:152` | Validate | `"job_search_agent" in options` → `True` → `next_node = "job_search_agent"` |
| `:169` | Task completion | `next_node != "__end__"` → skip |
| `:177` | Conversational reply | `conversational_response is None` → nothing appended |

**State mutation returned:**
```python
{"budget_stats": {"iterations": 1, "tool_calls": 0, "start_time": ...}, "next": "job_search_agent"}
```

### Conditional edge: `route_next()`

- `state.get("termination_signal")` → falsy (not set)
- `state.get("next")` → `"job_search_agent"` → returns `"job_search_agent"`

---

## Phase 4 — Career branch, cycle 1: job_search_agent executes

### Sub-node: `job_search_agent_node()`

**`agents/career/job_search.py`**

| Line | Action | Detail |
|------|--------|--------|
| `:49` | `messages = state.get("messages", [])` | Full message list |
| `:50` | `ProfileManager().load()` | Reads `data/user_profile.json` → `UserProfile` or default empty profile |
| `:51` | `profile.model_dump_json(indent=2)` | JSON string of user profile |
| `:52` | `ArtifactLoader.load_recent("career")` | Reads up to 3 most recent `.md`/`.txt` files from `data/career/artifacts/` by mtime, concatenates up to 4000 chars. Returns text or `"(no prior artifacts)"` |
| `:53` | `MemoryDistiller.load_summary()` | Second read of memory store this request |
| `:55` | Build system content | `PROMPT + memory + artifacts + profile_json` (~2000 token system prompt) |
| `:58` | `input_msgs` | `[SystemMessage(content=sys_content)] + messages` |
| `:61` | `react_agent.invoke({"messages": input_msgs})` | **ReAct loop begins** |

#### ReAct agent loop (`langgraph.prebuilt.create_react_agent`)

LLM: `gemini-3.1-pro-preview` (model_high_complexity). Tools: `search_jobs`, `tavily_search`, `robust_web_scrape`.

**ReAct iteration 1 — decide and call search_jobs:**

| Step | What happens |
|------|--------------|
| **LLM CALL #2** | Gemini receives system prompt + "find me remote Python jobs". Returns tool call: `search_jobs(query="remote Python developer", location="remote")` |
| Tool dispatch | LangGraph invokes `search_jobs` |

**`tools/search.py` → `search_jobs()`**

1. Builds `full_query = "remote Python developer remote job posting"`
2. **HTTP POST to Tavily API** with:
   - `search_depth="advanced"`
   - `include_answer=True`
   - `include_domains=["linkedin.com/jobs", "indeed.com", "glassdoor.com", "wellfound.com", "remoteok.com"]`
3. Formats response: `"AI Summary: ...\n\n---\n\nSource: https://...\nTitle: ...\nContent: ..."`
4. Returns formatted string → injected as `ToolMessage` into ReAct loop

**ReAct iteration 2 — optionally scrape a specific posting:**

| Step | What happens |
|------|--------------|
| **LLM CALL #3** | Gemini sees search results. May call `robust_web_scrape(url="https://...")` on a promising listing |
| Tool dispatch | LangGraph invokes `robust_web_scrape` |

**`tools/web_scraper.py` → `robust_web_scrape()` → `WebScraper.scrape()`**

1. `_check_cache(url)` — checks `data/cache/scraper/{md5(url)}.json`, verifies 24h TTL
2. On cache miss: `_make_request(url)`
   - SSRF check: resolves hostname, rejects private/loopback/reserved IPs
   - `requests.Session.get()` with `timeout=15`, `max_redirects=3`, streaming
   - Content-Length and streaming size cap at 10MB
   - `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))`
   - Returns 403/404 directly without raising
3. `BeautifulSoup(response.text, 'html.parser')` — parse HTML
4. Remove noise tags: `script`, `style`, `nav`, `footer`, `header`, `aside`, `iframe`, `noscript`
5. `_extract_main_content()` — tries `<main>`, `<article>`, `[role=main]`, `.content`, `#content`; falls back to `<body>`
6. `_extract_structured_data()` — parses `application/ld+json` scripts (job postings etc.)
7. `_extract_links()` — up to 15 relevant links with resolved relative URLs
8. `_clean_text()` — deduplicates whitespace, truncates at 10000 chars at paragraph boundary
9. `_save_cache()` — **writes** `{title, content, structured_data, links}` to `data/cache/scraper/{hash}.json`
10. Returns JSON string with `source`, `url`, `title`, `content`, `structured_data`, `links`

**ReAct iteration 3 — produce final report:**

| Step | What happens |
|------|--------------|
| **LLM CALL #4** | Gemini has all search + scrape results. Produces final Markdown table: `Target Role \| Company \| Location \| Why It's a Fit \| Link \| Next Action Step` |
| ReAct exits | No more tool calls in response |

**Back in `job_search_agent_node()`:**

| Line | Action | Detail |
|------|--------|--------|
| `:63` | Filter `ai_messages` | Only `AIMessage` with content and no `tool_calls` |
| `:64` | `final_content` | Last such message — the Markdown job report |
| `:69` | `task_id` | `"interactive_session"` |
| `:70` | `save_artifact("career", "job_search", "interactive_session", final_content)` | |

**`tools/save_artifact.py` → `save_artifact()`**

1. `artifact_dir = Path("data") / "career" / "artifacts"` → `mkdir(parents=True, exist_ok=True)`
2. `file_path = artifact_dir / "job_search_interactive_session.md"`
3. If file exists: appends timestamp suffix → `"job_search_interactive_session_1742911250.md"`
4. `file_path.write_text(content, encoding="utf-8")` — **writes artifact to disk**
5. Returns the `Path` object

**State mutation returned:**
```python
{
    "messages": [AIMessage(content="| Target Role | Company | ...", name="job_search_agent")],
    "termination_signal": True
}
```

LangGraph's `_add_messages` reducer appends the `AIMessage` to the existing list.

---

## Phase 5 — Career branch, cycle 2: supervisor routes to END

The sub-graph edge `job_search_agent → supervisor` fires unconditionally.

### Sub-node: `supervisor` (second invocation)

| Line | Action | Detail |
|------|--------|--------|
| `:102` | `stats` | `{"iterations": 1, ...}` |
| `:106` | `enforce_budget(state)` | `1 < 5` → no breach |
| `:125` | Task-status check | `task_manager.get_task("interactive_session")` → `None` → skip |
| `:143` | `stats["iterations"] += 1` | **iterations now 2** |
| `:146–148` | Load memory, build messages | Includes the `job_search_agent` AIMessage |
| `:151` | **LLM CALL #5** | `gemini-3-flash-preview` → sees completed job search output → `RouteParams(next="__end__", conversational_response=None)` |
| `:169` | Task completion | `next_node == "__end__"` and `task_manager.get_task("interactive_session")` → `None` → skip |

**State mutation returned:**
```python
{"budget_stats": {"iterations": 2, ...}, "next": "__end__"}
```

### Conditional edge: `route_next()`

- `state.get("termination_signal")` → `True` (set by `job_search_agent`)
- Returns `END`

Career branch sub-graph terminates. Control returns to the top-level graph.
Top-level edge `career_branch → END` fires. `orchestrator_graph.invoke()` returns the final state.

---

## Phase 6 — Response extraction and streaming

**Back in `websocket_chat()`**

| Step | Line | Action |
|------|------|--------|
| 9 | `:89` | `new_messages = result["messages"][1:]` — skip the 1 input `HumanMessage` |
| 10 | `:90–97` | Iterate `new_messages`. For each `AIMessage` send `{"type": "ai_message", "content": "...", "agent_name": "..."}`. In the happy path: one frame sent with `agent_name: "job_search_agent"` containing the Markdown report |
| 11 | `:100–105` | Memory distillation in executor |

**`_safe_distill()` → `MemoryDistiller.distill()`**

1. Takes last 10 messages, formats as `"User: ...\nAgent: ..."`
2. **LLM CALL #6**: `gemini-3-flash-preview.with_structured_output(DistillationResult)` — extracts up to 5 facts
3. Returns `DistillationResult(career_insights=["User seeks remote Python roles", ...], ...)`
4. `_read_store()` — reads `data/memory/context_store.json`
5. Merges new facts (dedup, cap at 15 per category)
6. `_write_store()` — **writes updated memory store to disk**

If `json.JSONDecodeError` is raised: resets store to `{}` and logs warning.
Any other exception: logged as non-fatal, silently swallowed.

| Step | Line | Action |
|------|------|--------|
| 12 | `:116` | Send to client: `{"type": "done"}` |

---

## Complete call chain summary

```
Frontend sendMessage()
  → WS frame: {"message": "find me remote Python jobs", "active_agent": "career"}

api/routes/chat.py::websocket_chat()
  → manager.connect()
  → websocket.receive_json()
  → get_checkpoint_config("career", thread_id)          → "career_{thread_id}"
  → websocket.send_json({"type": "status"})
  → orchestrator_graph.invoke(state, config)             [run_in_executor]

    orchestrator/graph.py::router_node()
      STATE: budget_stats = {iterations:0, tool_calls:0, start_time:now}

    orchestrator/graph.py::route_to_group()               → "career_branch"

    career_branch sub-graph:

      CYCLE 1:
        orchestrator/supervisor.py::supervisor_node()      [career closure]
          → enforce_budget()                               → {} (ok)
          → task_manager.get_task("interactive_session")   → None
          → MemoryDistiller.load_summary()                 → reads context_store.json
          → LLM CALL #1: gemini-3-flash-preview            → RouteParams(next="job_search_agent")
          STATE: {budget_stats.iterations:1, next:"job_search_agent"}

        route_next()                                       → "job_search_agent"

        agents/career/job_search.py::job_search_agent_node()
          → ProfileManager().load()                        → reads user_profile.json
          → ArtifactLoader.load_recent("career")           → reads data/career/artifacts/*.md
          → MemoryDistiller.load_summary()                 → reads context_store.json
          → react_agent.invoke()                           [ReAct loop, gemini-3.1-pro-preview]
              → LLM CALL #2                                → tool_call: search_jobs(...)
              → tools/search.py::search_jobs()
                  → TavilyClient.search()                  [HTTP POST to Tavily API, advanced depth]
                  → returns formatted job listing string
              → LLM CALL #3                                → tool_call: robust_web_scrape(url=...)
              → tools/web_scraper.py::WebScraper.scrape()
                  → _is_safe_url()                         [SSRF check]
                  → _check_cache()                         → cache miss
                  → _make_request()                        [HTTP GET, retry x3, 10MB cap]
                  → BeautifulSoup parse + noise removal
                  → _extract_main_content()
                  → _extract_structured_data()             [JSON-LD]
                  → _extract_links()
                  → _clean_text()                          [truncate at 10000 chars]
                  → _save_cache()                          WRITE: data/cache/scraper/{hash}.json
              → LLM CALL #4                                → final Markdown report
          → save_artifact("career","job_search",...)       WRITE: data/career/artifacts/job_search_interactive_session.md
          STATE: {messages:+[AIMessage(report,"job_search_agent")], termination_signal:True}

      CYCLE 2:
        orchestrator/supervisor.py::supervisor_node()
          → enforce_budget()                               → {} (ok, iterations=1)
          → MemoryDistiller.load_summary()
          → LLM CALL #5: gemini-3-flash-preview            → RouteParams(next="__end__")
          STATE: {budget_stats.iterations:2, next:"__end__"}

        route_next()
          → termination_signal is True                     → END

    career_branch → END (top-level graph)

  ← orchestrator_graph.invoke() returns final state

  → websocket.send_json({"type":"ai_message","content":"...","agent_name":"job_search_agent"})
  → _safe_distill(messages, "career")                     [run_in_executor]
      → LLM CALL #6: gemini-3-flash-preview                → DistillationResult
      → WRITE: data/memory/context_store.json
  → websocket.send_json({"type":"done"})
```

---

## Total external calls

| # | Call | Target | Model / Service |
|---|------|--------|-----------------|
| 1 | Supervisor routing (cycle 1) | Gemini | `gemini-3-flash-preview` |
| 2 | ReAct reasoning (step 1) | Gemini | `gemini-3.1-pro-preview` |
| 3 | `search_jobs` tool | Tavily API | HTTP POST |
| 4 | ReAct reasoning (step 2) | Gemini | `gemini-3.1-pro-preview` |
| 5 | `robust_web_scrape` tool | Target URL | HTTP GET (retry ×3 max) |
| 6 | ReAct reasoning (final) | Gemini | `gemini-3.1-pro-preview` |
| 7 | Supervisor routing (cycle 2) | Gemini | `gemini-3-flash-preview` |
| 8 | Memory distillation | Gemini | `gemini-3-flash-preview` |

Minimum calls (no scrape): 6. Maximum calls (scrape + retries): 8+ (retries add up to 2 extra HTTP calls per `_make_request`).

---

## Disk writes

| File | When |
|------|------|
| `data/checkpoints/overall_thread.db` | LangGraph `SqliteSaver` after every node completion |
| `data/cache/scraper/{md5(url)}.json` | After `robust_web_scrape` on cache miss |
| `data/career/artifacts/job_search_interactive_session.md` | After `job_search_agent_node` completes |
| `data/memory/context_store.json` | After memory distillation |

---

## State mutations through the graph

| After node | `budget_stats` | Other changes |
|------------|---------------|---------------|
| `router_node` | `{iterations:0, tool_calls:0, start_time:now}` | — |
| `supervisor` (cycle 1) | `iterations:1` | `next:"job_search_agent"` |
| `job_search_agent` | unchanged | `messages` += `[AIMessage(report)]`, `termination_signal:True` |
| `supervisor` (cycle 2) | `iterations:2` | `next:"__end__"` |
