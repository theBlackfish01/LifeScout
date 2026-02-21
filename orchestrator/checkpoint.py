import os
from pathlib import Path
from typing import Optional
from config.settings import settings

# Since langgraph v0.1.x, checkpointing relies on checkpointer instances
# We use langgraph-checkpoint-sqlite which provides SqliteSaver.
from langgraph.checkpoint.sqlite import SqliteSaver

# We keep a singleton pattern or connection factory for our checkpoint database.
# In a true persistent web app, we'd manage connections carefully (e.g., using AsyncSqliteSaver) 
# but for our synchronous/simple async MVP, a standard SqliteSaver connecting to a single file is sufficient.

_db_path = Path(settings.checkpoints_dir) / "overall_thread.db"

def get_checkpointer() -> SqliteSaver:
    """
    Returns an active SqliteSaver checkpointer instance.
    Ensure to use as a context manager if required by the graph compile() step,
    or pass the instance directly depending on langgraph versions.
    """
    # Create the checkpoints directory if it doesn't exist
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # We use a memory-safe file SQLite checkpointer.
    # The SqliteSaver.from_conn_string manages its own SQLite connections efficiently mapping thread_ids.
    return SqliteSaver.from_conn_string(str(_db_path))

def get_checkpoint_config(agent_group: str, thread_id: str) -> dict:
    """
    Returns the standard LangGraph RunnableConfig dict for a given thread.
    We namespace threads by agent_group and thread_id to prevent collision.
    """
    full_thread_id = f"{agent_group}_{thread_id}"
    return {"configurable": {"thread_id": full_thread_id}}
