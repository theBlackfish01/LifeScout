"""
Artifact library REST endpoints.
Replaces the /library slash command and provides access to generated files.
"""
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from context.artifact_manager import ArtifactManager
from models.artifact import Artifact
from config.settings import settings

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


@router.get("", response_model=List[Artifact])
async def list_all_artifacts():
    """List all artifacts across all agent groups."""
    all_artifacts = []
    for group in ["career", "life", "learning"]:
        all_artifacts.extend(ArtifactManager.list_artifacts(group))
    return all_artifacts


@router.get("/group/{agent_group}", response_model=List[Artifact])
async def list_artifacts_by_group(agent_group: str):
    """List artifacts for a specific agent group."""
    if agent_group not in ["career", "life", "learning"]:
        raise HTTPException(status_code=400, detail=f"Invalid agent group: {agent_group}")
    return ArtifactManager.list_artifacts(agent_group)


@router.get("/files/{agent_group}/{filename}")
async def download_artifact_file(agent_group: str, filename: str):
    """Download a specific artifact file by its filename."""
    file_path = Path(settings.data_dir) / agent_group / "artifacts" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return FileResponse(path=str(file_path), filename=filename)
