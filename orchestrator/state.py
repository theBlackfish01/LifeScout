from typing import TypedDict, List, Annotated
import operator
from langchain_core.messages import BaseMessage

def _add_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """Custom reducer for messages to ensure we don't just blindly append, 
    but for now simple append is fine for this MVP graph structure."""
    return left + right

class BudgetStats(TypedDict):
    iterations: int
    tool_calls: int
    start_time: float # time.time() float value

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], _add_messages]
    active_agent: str      # E.g., 'career', 'life', 'learning', etc.
    task_id: str           # UUID of the active Task
    budget_stats: BudgetStats
    next: str              # Routing flag used natively by our sub-graph logic
    termination_signal: bool  # Set True by agents/supervisors to signal graph should terminate
