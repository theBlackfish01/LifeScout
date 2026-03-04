from fastapi import APIRouter, File, UploadFile, HTTPException
import shutil
import os
from pathlib import Path
from config.settings import settings

router = APIRouter(prefix="/api/upload", tags=["Uploads"])

@router.post("/resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    artifact_dir = Path(settings.data_dir) / "career" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as latest_resume with appropriate extension
    save_path = artifact_dir / f"latest_resume{ext}"
    
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        file.file.close()

    return {"status": "success", "filename": file.filename, "saved_path": str(save_path)}
