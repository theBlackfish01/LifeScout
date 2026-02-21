import json
from pathlib import Path
from typing import List, Optional
from models.artifact import Artifact
from config.settings import settings

class ArtifactManager:
    @staticmethod
    def _get_index_path(agent_group: str) -> Path:
        return Path(settings.data_dir) / agent_group / "artifacts" / "index.json"

    @staticmethod
    def _load_index(agent_group: str) -> List[Artifact]:
        path = ArtifactManager._get_index_path(agent_group)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Artifact(**item) for item in data]
        except Exception as e:
            print(f"Error loading artifacts for {agent_group}: {e}")
            return []

    @staticmethod
    def _save_index(agent_group: str, artifacts: List[Artifact]) -> None:
        path = ArtifactManager._get_index_path(agent_group)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps([json.loads(a.model_dump_json()) for a in artifacts], indent=2))

    @staticmethod
    def register(artifact: Artifact) -> None:
        artifacts = ArtifactManager._load_index(artifact.agent_group)
        # Update if exists, else append
        for i, a in enumerate(artifacts):
            if a.id == artifact.id:
                artifacts[i] = artifact
                ArtifactManager._save_index(artifact.agent_group, artifacts)
                return
        artifacts.append(artifact)
        ArtifactManager._save_index(artifact.agent_group, artifacts)

    @staticmethod
    def retrieve(agent_group: str, artifact_id: str) -> Optional[Artifact]:
        artifacts = ArtifactManager._load_index(agent_group)
        for a in artifacts:
            if a.id == artifact_id:
                return a
        return None

    @staticmethod
    def list_artifacts(agent_group: str) -> List[Artifact]:
        return ArtifactManager._load_index(agent_group)
