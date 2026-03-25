# Testing Strategy

## Current State

The project has a `tests/` directory and references `pytest tests/ -v` in build commands, but the test suite is minimal/in-progress.

## Commands

### Backend
```bash
pytest tests/ -v                                              # All tests
pytest tests/test_specific.py -v                              # Single file
pytest tests/test_specific.py::test_function_name -v          # Single test
mypy api/ agents/ orchestrator/ --ignore-missing-imports      # Type checking
```

### Frontend
```bash
cd frontend && npm test                                        # Jest/Vitest (if configured)
cd frontend && npx tsc --noEmit                                # Type checking
cd frontend && npm run lint                                    # ESLint
```

## Recommended Test Layers

### Unit Tests (agents/)
- Test each agent node function in isolation
- Mock `ProfileManager.load()`, `ArtifactLoader.load_recent()`, `MemoryDistiller.load_summary()`
- Mock LLM calls (`ChatGoogleGenerativeAI.invoke`)
- Verify returned dict shape matches `AgentState` (has `messages` key, correct `name` field)
- Verify artifact file creation

### Unit Tests (context/)
- Test each manager with temp directories
- `TaskManager`: verify lifecycle (pending → running → completed), queue enforcement, stale cleanup
- `ArtifactManager`: register, retrieve, list operations
- `MemoryDistiller`: verify distillation output shape, max items cap

### Unit Tests (tools/)
- Mock external APIs (Tavily, requests)
- `WebScraper`: test cache hit/miss, SSRF protection, content truncation
- `DocumentGenerator`: test PDF/DOCX output with sample markdown
- `save_artifact`: verify file path construction and ArtifactManager registration

### Integration Tests (orchestrator/)
- Test graph execution end-to-end with mocked LLMs
- Verify routing: `active_agent="career"` → career_branch invoked
- Verify budget enforcement: exceed MAX_ITERATIONS → `[SYSTEM] Budget Exceeded` message
- Verify supervisor routing: structured output → correct sub-agent node

### API Tests (api/)
- Test REST endpoints with FastAPI `TestClient`
- Test WebSocket flow: connect → send message → receive status/ai_message/done
- Test file upload validation (reject non-PDF/DOCX)
- Test CORS headers

### Frontend Tests
- Component rendering with React Testing Library
- Zustand store actions (mock WebSocket, verify state transitions)
- WebSocket message parsing (ai_message, done, error handling)

## Key Mocking Points

| Dependency | Mock Strategy |
|------------|---------------|
| `ChatGoogleGenerativeAI` | Patch `.invoke()` to return canned `AIMessage` |
| `TavilyClient` | Patch `search()` to return sample results |
| `requests.get` | Patch for web scraper tests |
| `ProfileManager.load()` | Return fixture `UserProfile` |
| `MemoryDistiller.load_summary()` | Return static string |
| `WebSocket` | Use FastAPI `TestClient.websocket_connect()` |

## Environment for Tests

Set in test fixtures or `.env.test`:
```
GEMINI_API_KEY=test-key
TAVILY_API_KEY=test-key
```

Use `tmp_path` pytest fixture for data directory isolation.
