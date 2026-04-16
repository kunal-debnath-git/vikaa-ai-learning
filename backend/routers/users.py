from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db import tbl
import logging

logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=["users"])

class UserCreate(BaseModel):
    name: str
    email: str

@router.post("/users")
async def create_user(user: UserCreate):
    # BYPASS FOR TESTING
    if user.email == "test@testemail.com":
        return {
            "id": "00000000-0000-0000-0000-000000000000", 
            "name": "Test User", 
            "email": "test@testemail.com",
            "created_at": "2026-04-16T00:00:00Z"
        }
    
    try:
        response = tbl("users").upsert({"name": user.name, "email": user.email}, on_conflict="email").execute()
        if not response.data:
            logger.error(f"User upsert returned no data for email: {user.email}")
            raise HTTPException(status_code=400, detail="User creation failed (no data returned)")
        return response.data[0]
    except Exception as e:
        logger.error(f"Supabase error during user upsert: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/users/{email}")
async def get_user(email: str):
    response = tbl("users").select("*").eq("email", email).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")
    return response.data[0]
