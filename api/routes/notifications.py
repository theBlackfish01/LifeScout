import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from config.settings import settings

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

NOTIFICATIONS_FILE = Path(settings.data_dir) / "notifications.json"

class Notification(BaseModel):
    id: str
    title: str
    message: str
    type: str # "info", "success", "warning", "career", "life"
    link: Optional[str] = None
    read: bool = False
    timestamp: float

def _load_notifications() -> List[dict]:
    if not NOTIFICATIONS_FILE.exists():
        return []
    try:
        with open(NOTIFICATIONS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_notifications(notifs: List[dict]):
    NOTIFICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFICATIONS_FILE, "w") as f:
        json.dump(notifs, f, indent=2)

@router.get("")
async def get_notifications():
    notifs = _load_notifications()
    # Sort newest first
    return sorted(notifs, key=lambda x: x["timestamp"], reverse=True)

@router.put("/{notif_id}/read")
async def mark_read(notif_id: str):
    notifs = _load_notifications()
    for n in notifs:
        if n["id"] == notif_id:
            n["read"] = True
            break
    _save_notifications(notifs)
    return {"status": "success"}

# Internal helper function for the scheduler to create notifications
def create_notification(title: str, message: str, notif_type: str = "info", link: str = None):
    notifs = _load_notifications()
    new_notif = {
        "id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "type": notif_type,
        "link": link,
        "read": False,
        "timestamp": datetime.now().timestamp()
    }
    notifs.append(new_notif)
    _save_notifications(notifs)
    print(f"[Notifications] Created: {title}")
