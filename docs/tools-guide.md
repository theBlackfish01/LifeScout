# Tools Guide

## Available Tools

All tools are in `tools/`. Agents bind tools via `create_react_agent(llm, tools)` or `llm.bind_tools([...])`.

### `tavily_search(query: str, search_depth: str = "basic") -> str`
**File:** `tools/search.py`
Generic web search via Tavily API. Returns formatted string with AI summary + source snippets.

### `search_jobs(query: str, location: str = "") -> str`
**File:** `tools/search.py`
Job-specific search. Uses `search_depth="advanced"` with domain filtering: LinkedIn, Indeed, Glassdoor, Wellfound, RemoteOK.

### `search_courses(query: str) -> str`
**File:** `tools/search.py`
Course-specific search. Uses `search_depth="advanced"` with domain filtering: Coursera, Udemy, edX, Pluralsight, LinkedIn Learning.

### `robust_web_scrape(url: str, bypass_cache: bool = False) -> str`
**File:** `tools/web_scraper.py`
Scrapes URL and returns JSON string with: `title`, `content`, `structured_data` (JSON-LD), `links`.

Features:
- 24h file cache in `data/cache/scraper/{url_hash}.json`
- SSRF protection (`_is_safe_url`)
- 10MB download limit
- Retry with exponential backoff
- Content truncation at 10,000 chars

### `save_artifact(agent_group: str, task_id: str, artifact_type: str, title: str, format_type: str, content: str) -> str`
**File:** `tools/file_manager.py`
Saves artifact file and registers with `ArtifactManager`.
- Path: `data/{agent_group}/artifacts/{safe_title}_{uuid[:8]}.{ext}`
- Returns: `"Successfully saved artifact to {path}. ID: {id}"`

### `read_safe_context(file_path: str) -> str`
**File:** `tools/file_manager.py`
Reads files within `data/` directory. Path traversal protection via `.resolve()` prefix check.

### `generate_document(content_md: str, output_path: str, format_type: str = "pdf") -> str`
**File:** `tools/document_generator.py`
Converts Markdown to PDF (WeasyPrint with CSS) or DOCX (python-docx with header parsing).

### `parse_document(file_path: str) -> str`
**File:** `tools/document_parser.py`
Extracts text from PDF, DOCX, TXT, MD, CSV. Returns raw text with page separators for PDFs.

---

## Context Managers (tools/context/)

Not LangChain tools — these are utility classes used by agents directly.

### `ProfileManager` (`context/profile_manager.py`)
```python
ProfileManager.load() -> UserProfile      # data/user_profile.json
ProfileManager.save(profile: UserProfile)
```

### `ArtifactManager` (`context/artifact_manager.py`)
```python
ArtifactManager.register(artifact: Artifact)
ArtifactManager.retrieve(agent_group, artifact_id) -> Optional[Artifact]
ArtifactManager.list_artifacts(agent_group) -> List[Artifact]
```
Index files: `data/{group}/artifacts/index.json`

### `ArtifactLoader` (in `context/`)
```python
ArtifactLoader.load_recent(group, limit=3, max_chars=4000) -> str   # For system prompt injection
ArtifactLoader.load_specific(group, filename) -> Optional[str]
```

### `TaskManager` (`context/task_manager.py`)
```python
task_manager.register_task(task: Task)
task_manager.update_task(task: Task)
task_manager.get_task(task_id) -> Optional[Task]
task_manager.get_tasks_by_group(agent_group) -> List[Task]
```
- Singleton instance: `task_manager`
- One active (running) task per domain enforced by `_evaluate_queue()`
- On startup: cancels stale running tasks
- Log files: `data/{group}/logs/{task_id}.json`

### `MemoryDistiller` (`context/memory_distiller.py`)
```python
MemoryDistiller.distill(messages, agent_group)  # Async, called after chat response
MemoryDistiller.load_summary() -> str            # ~300 token formatted summary
```
- Extracts: `career_insights`, `life_insights`, `learning_insights`, `cross_domain_goals`, `action_items`
- Max 15 items per category
- Store: `data/memory/context_store.json`

### `GoalManager` (`context/goal_manager.py`)
```python
GoalManager.list_goals(agent_group) -> List[Goal]
GoalManager.create(goal: Goal)
GoalManager.update(goal: Goal)
GoalManager.delete(agent_group, goal_id)
```
Files: `data/{group}/goals/goals.json`

### `ConversationManager` (`context/conversation_manager.py`)
```python
ConversationManager.load(agent_group, session_id) -> Optional[ConversationSession]
ConversationManager.save(session: ConversationSession)
```
Files: `data/{group}/conversations/{session_id}.json`

### `ArtifactCurator` (`context/artifact_curator.py`)
```python
ArtifactCurator.curate(group, max_age_days=30) -> {"archived": int, "deleted": int, "remaining": int}
```

---

## Implementing a New Tool

1. Create function in `tools/` with `@tool` decorator (LangChain)
2. Must have docstring with `Args:` and `Returns:` sections
3. Import in the agent file that needs it
4. Pass to `create_react_agent(llm, [your_tool])` or `llm.bind_tools([your_tool])`
5. Never write to `data/` directly from tools — use `save_artifact()` or context managers
