"""
Centralized artifact writer with collision prevention.
All agents must use this instead of raw open() calls.
"""
import time
from pathlib import Path
from config.settings import settings


def save_artifact(group: str, name: str, task_id: str, content: str) -> Path:
    """
    Save an artifact to disk with collision-safe naming.

    Args:
        group: Agent group ("career", "life", "learning").
        name: Artifact base name (e.g. "resume", "goals", "study_plan").
        task_id: Task UUID or "manual"/"interactive_session".
        content: The text content to write.

    Returns:
        The Path where the artifact was saved.
    """
    artifact_dir = Path(settings.data_dir) / group / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    file_path = artifact_dir / f"{name}_{task_id}.md"

    # Collision prevention: if file already exists, append a timestamp suffix
    if file_path.exists():
        ts = int(time.time())
        file_path = artifact_dir / f"{name}_{task_id}_{ts}.md"

    file_path.write_text(content, encoding="utf-8")
    return file_path
