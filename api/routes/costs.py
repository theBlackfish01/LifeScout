"""
Cost tracking REST endpoints.
Exposes accumulated token usage per agent per session.
"""
from typing import List
from fastapi import APIRouter, HTTPException
from observability.cost_tracker import cost_tracker

router = APIRouter(prefix="/api/costs", tags=["Costs"])


@router.get("")
async def list_all_costs():
    """Return token-usage summaries for all tracked sessions."""
    return cost_tracker.get_all_sessions()


@router.get("/{thread_id}")
async def get_session_costs(thread_id: str):
    """Return token-usage breakdown for a single session."""
    data = cost_tracker.get_session(thread_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No cost data for thread {thread_id}")
    return data
