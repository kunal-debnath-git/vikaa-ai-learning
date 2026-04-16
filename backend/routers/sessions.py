from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from backend.db import tbl, bypass_session
from backend.config import settings
from datetime import datetime

router = APIRouter(tags=["sessions"])

class SessionCreate(BaseModel):
    user_id: str
    role: str
    difficulty: str
    llm_provider: str
    brain_mode: str = "llm"
    categories: Dict[str, List[str]]

@router.post("/sessions")
async def create_session(session: SessionCreate):
    # BYPASS FOR TESTING
    if session.user_id == "00000000-0000-0000-0000-000000000000":
        total = settings.config.get("session_config", {}).get("questions_per_session", 20)
        bypass_session.update({
            "role": session.role,
            "difficulty": session.difficulty,
            "llm_provider": session.llm_provider,
            "brain_mode": session.brain_mode,
            "categories": session.categories,
            "total_questions": total,
        })
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": session.user_id,
            "role": session.role,
            "difficulty": session.difficulty,
            "llm_provider": session.llm_provider,
            "brain_mode": session.brain_mode,
            "categories": session.categories,
            "total_questions": total,
            "score": 0,
            "completed": False,
            "started_at": datetime.now().isoformat()
        }

    data = {
        "user_id": session.user_id,
        "role": session.role,
        "difficulty": session.difficulty,
        "llm_provider": session.llm_provider,
        "brain_mode": session.brain_mode,
        "categories": session.categories,
        "total_questions": settings.config.get("session_config", {}).get("questions_per_session", 20),
        "score": 0,
        "completed": False
    }
    response = tbl("sessions").insert(data).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Session creation failed")
    return response.data[0]

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    response = tbl("sessions").select("*").eq("id", session_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return response.data[0]

@router.patch("/sessions/{session_id}/complete")
async def complete_session(session_id: str, score: int):
    # BYPASS FOR TESTING
    if session_id == "11111111-1111-1111-1111-111111111111":
        return {
            "id": session_id,
            "user_id": "00000000-0000-0000-0000-000000000000",
            "role": bypass_session.get("role", "architect"),
            "difficulty": bypass_session.get("difficulty", "Medium"),
            "brain_mode": bypass_session.get("brain_mode", "llm"),
            "score": score,
            "completed": True,
            "completed_at": datetime.now().isoformat()
        }

    response = tbl("sessions").update({
        "completed": True,
        "score": score,
        "completed_at": datetime.now().isoformat()
    }).eq("id", session_id).execute()
    return response.data[0]
