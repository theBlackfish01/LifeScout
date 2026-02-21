import os
import uuid
from pathlib import Path
from typing import Optional, List
from config.settings import settings
from context.artifact_manager import ArtifactManager
from models.artifact import Artifact
from langchain_core.tools import tool

class FileManager:
    """
    Proxy overlay to ensure Agents can manage artifacts across the system boundaries
    without needing raw OS module privileges scattered through their prompts.
    """
    
    @staticmethod
    def _validate_group(group: str) -> bool:
        return group in ["career", "life", "learning"]

    @staticmethod
    def save_agent_artifact(agent_group: str, task_id: str, artifact_type: str, title: str, 
                            file_format: str, content: str | bytes) -> str:
        """
        Saves an artifact safely into the predefined directory constraints matching the Tech Plan.
        """
        if not FileManager._validate_group(agent_group):
            return f"Error: Invalid agent group '{agent_group}'"
        
        # Determine path
        artifact_id = str(uuid.uuid4())
        ext = file_format.lower().replace(".", "")
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        filename = f"{safe_title}_{artifact_id[:8]}.{ext}"
        
        dir_path = Path(settings.data_dir) / agent_group / "artifacts"
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / filename

        try:
            mode = "wb" if isinstance(content, bytes) else "w"
            encoding = None if isinstance(content, bytes) else "utf-8"
            
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
                
            # Register with Context Manager
            artifact = Artifact(
                id=artifact_id,
                task_id=task_id,
                agent_group=agent_group,
                type=artifact_type,
                title=title,
                file_path=str(file_path),
                format=ext,   # type: ignore
                version=1
            )
            ArtifactManager.register(artifact)
            
            return f"Successfully saved artifact to {file_path}. ID: {artifact_id}"
            
        except Exception as e:
            return f"Error saving artifact: {str(e)}"

    @staticmethod
    def read_file_safe(file_path: str) -> str:
        """
        Safely reads file paths that exist within the local `./data` mount constraint.
        """
        p = Path(file_path).resolve()
        safe_root = Path(settings.data_dir).resolve()
        
        # Ensure path traversal does not break outside of data dir
        if not str(p).startswith(str(safe_root)):
             return f"Error: Access Denied. {p} is outside of the configured safe data context."
             
        if not p.exists():
            return f"Error: File not found at {file_path}"
            
        try:
             with open(p, "r", encoding="utf-8") as f:
                 return f.read()
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}"

_file_manager_instance = FileManager()

@tool
def save_artifact(agent_group: str, task_id: str, artifact_type: str, title: str, format_type: str, content: str) -> str:
    """
    Saves generated text content directly to the shared file system context matching Data Model constraints.
    Agents use this to persist raw MD/JSON strings into the context layer index.
    
    Args:
        agent_group: Either 'career', 'life', or 'learning'.
        task_id: UUID of the task handling this interaction.
        artifact_type: E.g., 'resume', 'report', 'study_plan'
        title: Human readable title for the file.
        format_type: E.g., 'md' or 'json'
        content: The text payload to write to disk.
    """
    return _file_manager_instance.save_agent_artifact(
        agent_group, task_id, artifact_type, title, format_type, content
    )

@tool
def read_safe_context(file_path: str) -> str:
    """
    Reads a string from an existing file stored within the `data/` safe context limits.
    
    Args:
        file_path: Absolute or relative local path inside the boundaries (e.g., 'data/user_profile.json').
    """
    return _file_manager_instance.read_file_safe(file_path)
