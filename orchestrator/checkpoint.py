import os
from pathlib import Path
from typing import Optional
from config.settings import settings

# Since langgraph v0.1.x, checkpointing relies on checkpointer instances
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

_db_path = Path(settings.checkpoints_dir) / "overall_thread.db"

# We keep a singleton pattern or connection factory for our checkpoint database.
_conn = None

def get_checkpointer() -> SqliteSaver:
    global _conn
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    if _conn is None:
        # check_same_thread=False is needed for graph execution traversing different threads/async contexts
        _conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    
    return SqliteSaver(_conn)

def get_checkpoint_config(agent_group: str, thread_id: str) -> dict:
    """
    Returns the standard LangGraph RunnableConfig dict for a given thread.
    We namespace threads by agent_group and thread_id to prevent collision.
    """
    full_thread_id = f"{agent_group}_{thread_id}"
    return {"configurable": {"thread_id": full_thread_id}}
