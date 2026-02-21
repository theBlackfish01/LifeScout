import json
from pathlib import Path
from typing import Optional
from models.conversation import ConversationSession
from config.settings import settings

class ConversationManager:
    @staticmethod
    def _get_path(agent_group: str, session_id: str) -> Path:
        return Path(settings.data_dir) / agent_group / "conversations" / f"{session_id}.json"

    @staticmethod
    def load(agent_group: str, session_id: str) -> Optional[ConversationSession]:
        path = ConversationManager._get_path(agent_group, session_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ConversationSession(**data)
        except Exception as e:
            print(f"Error loading conversation session {session_id}: {e}")
            return None

    @staticmethod
    def save(session: ConversationSession) -> None:
        path = ConversationManager._get_path(session.agent_group, session.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(session.model_dump_json(indent=2))
