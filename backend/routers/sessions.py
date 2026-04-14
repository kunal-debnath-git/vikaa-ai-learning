from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from backend.db import db
from datetime import datetime

router = APIRouter(tags=["sessions"])

class SessionCreate(BaseModel):
    user_id: str
    role: str
    difficulty: str
    llm_provider: str
    categories: Dict[str, List[str]]

@router.post("/sessions")
async def create_session(session: SessionCreate):
    data = {
        "user_id": session.user_id,
        "role": session.role,
        "difficulty": session.difficulty,
        "llm_provider": session.llm_provider,
        "categories": session.categories,
        "total_questions": 20,
        "score": 0,
        "completed": False
    }
    response = db.table("sessions").insert(data).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Session creation failed")
    return response.data[0]

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    response = db.table("sessions").select("*").eq("id", session_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return response.data[0]

@router.patch("/sessions/{session_id}/complete")
async def complete_session(session_id: str, score: int):
    response = db.table("sessions").update({
        "completed": True,
        "score": score,
        "completed_at": datetime.now().isoformat()
    }).eq("id", session_id).execute()
    return response.data[0]
