from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime
import uuid

class Milestone(BaseModel):
    title: str
    status: Literal["pending", "completed"] = "pending"
    completed_at: Optional[datetime] = None

class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_group: str
    title: str
    status: Literal["active", "completed", "paused"] = "active"
    progress: float = 0.0  # 0.0 to 1.0
    milestones: List[Milestone] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
