# API Protocol

## WebSocket Chat Protocol

### Endpoint
```
ws://{host}/api/chat/{thread_id}
```

`thread_id` format from frontend: `{activeAgent}-session` (e.g., `career-session`)

### Client → Server

```json
{
  "message": "user input text",
  "active_agent": "career|life|learning|onboarding|settings"
}
```

### Server → Client

Messages sent sequentially in this order:

**1. Status (processing started)**
```json
{"type": "status", "content": "processing"}
```

**2. AI Message(s) (one per agent response)**
```json
{"type": "ai_message", "content": "response text", "agent_name": "resume_agent"}
```

**3. Completion**
```json
{"type": "done"}
```

**Error (replaces done on failure)**
```json
{"type": "error", "content": "error description"}
```

### Connection Lifecycle
1. Client connects with WebSocket
2. Server accepts connection, registers in `ConnectionManager`
3. Client sends message JSON
4. Server invokes LangGraph, streams responses
5. After response, server triggers `MemoryDistiller.distill()` async
6. Connection persists for next message (frontend reconnects on agent switch)

### Frontend WebSocket Handling (`useAppStore.connectWs`)
- Creates WebSocket to `ws://{API_BASE}/api/chat/{threadId}` (strips http://)
- On `ai_message`: adds to messages array with `role: "ai"`, `agentName` from payload
- On `done`: sets `isProcessing = false`
- On `error`: adds error as system message, sets `isProcessing = false`
- On agent switch (`setActiveAgent`): closes existing WS, clears messages

---

## REST Endpoints

### Health Check
```
GET /health → {"status": "ok", "service": "lifescouter-api"}
```

### Profile
```
GET  /api/profile                → UserProfile
PUT  /api/profile                → UserProfile  (body: UserProfile JSON)
GET  /api/profile/onboarding-status → {"onboarding_complete": bool}
```

### Tasks
```
GET /api/tasks                   → List[Task]
GET /api/tasks/group/{group}     → List[Task]
GET /api/tasks/{task_id}         → Task
```

### Artifacts
```
GET /api/artifacts                        → List[Artifact]
GET /api/artifacts/group/{agent_group}    → List[Artifact]
GET /api/artifacts/files/{group}/{file}   → FileResponse (download)
```

### Uploads
```
POST /api/upload/resume          → {"status": "success", "filename": str, "saved_path": str}
```
- Content-Type: multipart/form-data, field name: `file`
- Accepted extensions: `.pdf`, `.docx`, `.doc`
- Saved to: `data/career/artifacts/latest_resume{ext}`

### Notifications
```
GET /api/notifications           → List[Notification]  (newest first)
PUT /api/notifications/{id}/read → {"status": "success"}
```

---

## Data Models (Pydantic Schemas)

### UserProfile
```python
UserProfile:
  id: str (UUID)
  name: str = ""
  age: Optional[int]
  location: str = ""
  current_status: Optional[Literal["student", "working", "transitioning"]]
  field: str = ""
  goals: UserGoals {career: List[str], life: List[str], learning: List[str]}
  constraints: UserConstraints {time_per_week: Optional[int], budget: Optional[Literal["low","medium","high"]], commitments: List[str]}
  preferences: UserPreferences {communication_style: Optional[Literal["formal","casual"]]}
  onboarding_complete: bool = False
  created_at: datetime
  updated_at: datetime
```

### Task
```python
Task:
  id: str (UUID)
  trigger: Literal["user_initiated", "scheduled"]
  agent_group: Literal["career", "life", "learning"]
  sub_agent: str
  title: str
  plan: TaskPlan {steps: List[str], estimated_time: Optional[str]}
  status: Literal["pending", "running", "completed", "failed", "cancelled"]
  thread_id: str
  created_at: datetime
  completed_at: Optional[datetime]
  result: TaskResult {artifact_ids: List[str], summary: str = ""}
  feedback: TaskFeedback {rating: Optional[int], issues: List[str], comments: str = ""}
```

### Artifact
```python
Artifact:
  id: str (UUID)
  task_id: str
  agent_group: Literal["career", "life", "learning"]
  type: str  # resume, study_plan, report, analysis, tracker, lead_batch
  title: str
  file_path: str
  format: Literal["pdf", "docx", "md", "json"]
  version: int = 1
  created_at: datetime
```

### Notification
```python
Notification:
  id: str
  title: str
  message: str
  type: str  # "info", "success", "warning", "career", "life"
  link: Optional[str] = None
  read: bool = False
  timestamp: float
```

### Goal
```python
Goal:
  id: str (UUID)
  agent_group: str
  title: str
  status: Literal["active", "completed", "paused"]
  progress: float  # 0.0 to 1.0
  milestones: List[Milestone {title: str, status: Literal["pending","completed"], completed_at: Optional[datetime]}]
  created_at: datetime
  updated_at: datetime
```

---

## CORS

Allowed origins: `http://localhost:3000`, `http://127.0.0.1:3000`
All methods, all headers, credentials enabled.
