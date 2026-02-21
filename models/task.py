from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from datetime import datetime
import uuid

class TaskPlan(BaseModel):
    steps: List[str] = Field(default_factory=list)
    estimated_time: Optional[str] = None

class TaskResult(BaseModel):
    artifact_ids: List[str] = Field(default_factory=list)
    summary: str = ""

class TaskFeedback(BaseModel):
    rating: Optional[int] = None
    issues: List[str] = Field(default_factory=list)
    comments: str = ""

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger: Literal["user_initiated", "scheduled"]
    agent_group: Literal["career", "life", "learning"]
    sub_agent: str  # e.g., resume, job_search, lead_generation
    title: str
    plan: TaskPlan = Field(default_factory=TaskPlan)
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = "pending"
    thread_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result: TaskResult = Field(default_factory=TaskResult)
    feedback: TaskFeedback = Field(default_factory=TaskFeedback)
