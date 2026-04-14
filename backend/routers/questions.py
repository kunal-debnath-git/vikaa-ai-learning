from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.db import db
from backend.question_gen import generate_questions

router = APIRouter(tags=["questions"])

@router.post("/sessions/{session_id}/generate")
async def generate_session_questions(session_id: str):
    # Fetch session info
    session_resp = db.table("sessions").select("*").eq("id", session_id).execute()
    if not session_resp.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_resp.data[0]
    
    # Generate questions via LLM
    questions = await generate_questions(
        role=session["role"],
        difficulty=session["difficulty"],
        categories=session["categories"],
        llm_provider=session["llm_provider"]
    )
    
    # Store questions in DB
    for q in questions:
        q["session_id"] = session_id
        db.table("questions").insert(q).execute()
        
    return {"status": "success", "count": len(questions)}

@router.get("/sessions/{session_id}/questions")
async def get_questions(session_id: str):
    response = db.table("questions").select("*").eq("session_id", session_id).order("question_number").execute()
    return response.data

class AnswerSubmit(BaseModel):
    question_id: str
    user_answer: str
    time_taken_seconds: int

@router.post("/sessions/{session_id}/answers")
async def submit_answer(session_id: str, answer: AnswerSubmit):
    # Get the question to check the correct answer
    q_resp = db.table("questions").select("*").eq("id", answer.question_id).execute()
    if not q_resp.data:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question = q_resp.data[0]
    is_correct = (answer.user_answer == question["correct_answer"])
    
    # Store the answer
    ans_data = {
        "session_id": session_id,
        "question_id": answer.question_id,
        "user_answer": answer.user_answer,
        "is_correct": is_correct,
        "time_taken_seconds": answer.time_taken_seconds
    }
    db.table("answers").insert(ans_data).execute()
    
    # Update performance tracking (simplified version)
    # In a real app, this should be an atomic upsert
    user_id_resp = db.table("sessions").select("user_id, difficulty").eq("id", session_id).execute()
    if user_id_resp.data:
        u_info = user_id_resp.data[0]
        perf_resp = db.table("performance_tracking").select("*").match({
            "user_id": u_info["user_id"],
            "category": question["category"],
            "difficulty": u_info["difficulty"]
        }).execute()
        
        if perf_resp.data:
            perf = perf_resp.data[0]
            db.table("performance_tracking").update({
                "total_attempted": perf["total_attempted"] + 1,
                "total_correct": perf["total_correct"] + (1 if is_correct else 0)
            }).eq("id", perf["id"]).execute()
        else:
            db.table("performance_tracking").insert({
                "user_id": u_info["user_id"],
                "category": question["category"],
                "subcategory": question.get("subcategory"),
                "difficulty": u_info["difficulty"],
                "total_attempted": 1,
                "total_correct": 1 if is_correct else 0
            }).execute()

    return {
        "is_correct": is_correct,
        "correct_answer": question["correct_answer"],
        "explanation": question["explanation"],
        "learning_guidance": question["learning_guidance"] if not is_correct else None
    }
