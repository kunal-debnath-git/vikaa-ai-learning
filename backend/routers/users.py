from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db import db

router = APIRouter(tags=["users"])

class UserCreate(BaseModel):
    name: str
    email: str

@router.post("/users")
async def create_user(user: UserCreate):
    response = db.table("users").upsert({"name": user.name, "email": user.email}, on_conflict="email").execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="User creation failed")
    return response.data[0]

@router.get("/users/{email}")
async def get_user(email: str):
    response = db.table("users").select("*").eq("email", email).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")
    return response.data[0]
