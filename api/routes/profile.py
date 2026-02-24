"""
Profile REST endpoints.
Replaces the /profile slash command and provides GET/PUT for the UserProfile.
"""
from fastapi import APIRouter, HTTPException
from context.profile_manager import ProfileManager
from models.user_profile import UserProfile

router = APIRouter(prefix="/api/profile", tags=["Profile"])

profile_mgr = ProfileManager()


@router.get("", response_model=UserProfile)
async def get_profile():
    """Retrieve the current user profile."""
    profile = profile_mgr.load()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile found. Complete onboarding first.")
    return profile


@router.put("", response_model=UserProfile)
async def update_profile(profile: UserProfile):
    """Update the entire user profile."""
    profile_mgr.save(profile)
    return profile


@router.get("/onboarding-status")
async def get_onboarding_status():
    """Check whether onboarding has been completed."""
    profile = profile_mgr.load()
    return {"onboarding_complete": profile.onboarding_complete if profile else False}
