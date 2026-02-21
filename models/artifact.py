from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
import uuid

class Artifact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    agent_group: Literal["career", "life", "learning"]
    type: str  # resume, study_plan, report, analysis, tracker, lead_batch
    title: str
    file_path: str
    format: Literal["pdf", "docx", "md", "json"]
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
