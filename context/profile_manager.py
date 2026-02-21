import json
import os
from pathlib import Path
from models.user_profile import UserProfile
from config.settings import settings

PROFILE_PATH = Path(settings.data_dir) / "user_profile.json"

class ProfileManager:
    @staticmethod
    def load() -> UserProfile:
        if not PROFILE_PATH.exists():
            # Return a default empty profile if it doesn't exist
            return UserProfile()
        
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return UserProfile(**data)
        except Exception as e:
            print(f"Error loading UserProfile from {PROFILE_PATH}: {e}")
            return UserProfile()

    @staticmethod
    def save(profile: UserProfile) -> None:
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            # We use dump with default string conversion since Pydantic provides JSON-compatible dicts
            # For pydantic v2: model_dump_json() usually handles datetimes. 
            # Given we specified pydantic in requirements, let's use model_dump_json.
            f.write(profile.model_dump_json(indent=2))
