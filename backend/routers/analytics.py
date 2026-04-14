from fastapi import APIRouter
from backend.db import db

router = APIRouter(tags=["analytics"])

@router.get("/users/{user_id}/performance")
async def get_user_performance(user_id: str):
    response = db.table("performance_tracking").select("*").eq("user_id", user_id).execute()
    return response.data

@router.get("/users/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    response = db.table("sessions").select("*").eq("user_id", user_id).order("started_at", desc=True).execute()
    return response.data

@router.get("/config")
async def get_config():
    from backend.config import settings
    return settings.config
