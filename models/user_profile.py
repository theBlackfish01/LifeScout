from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from datetime import datetime
import uuid

class UserGoals(BaseModel):
    career: List[str] = Field(default_factory=list)
    life: List[str] = Field(default_factory=list)
    learning: List[str] = Field(default_factory=list)

class UserConstraints(BaseModel):
    time_per_week: Optional[int] = None
    budget: Optional[Literal["low", "medium", "high"]] = None
    commitments: List[str] = Field(default_factory=list)

class UserPreferences(BaseModel):
    communication_style: Optional[Literal["formal", "casual"]] = None

class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    age: Optional[int] = None
    location: str = ""
    current_status: Optional[Literal["student", "working", "transitioning"]] = None
    field: str = ""
    goals: UserGoals = Field(default_factory=UserGoals)
    constraints: UserConstraints = Field(default_factory=UserConstraints)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    onboarding_complete: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
