"""
Task queue REST endpoints.
Replaces the /dashboard slash command and provides visibility into background tasks.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from context.task_manager import task_manager
from models.task import Task

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("", response_model=List[Task])
async def list_all_tasks():
    """List all tasks across all agent groups."""
    all_tasks = []
    for group in ["career", "life", "learning"]:
        all_tasks.extend(task_manager.get_tasks_by_group(group))
    return all_tasks


@router.get("/group/{agent_group}", response_model=List[Task])
async def list_tasks_by_group(agent_group: str):
    """List tasks for a specific agent group."""
    if agent_group not in ["career", "life", "learning"]:
        raise HTTPException(status_code=400, detail=f"Invalid agent group: {agent_group}")
    return task_manager.get_tasks_by_group(agent_group)


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """Retrieve a specific task by its ID."""
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return task
