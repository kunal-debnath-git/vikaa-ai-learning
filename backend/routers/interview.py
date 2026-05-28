import asyncio
import uuid
import pathlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.config import settings

_ROOT = pathlib.Path(__file__).parent.parent.parent

router = APIRouter(tags=["interview"])

# In-memory session store — v1, no DB persistence needed
_sessions: dict = {}

# ── Style instruction blocks injected into the system prompt ─────────────────

_STYLE_PROMPTS = {
    "mixed": (
        "Mix behavioral (STAR), technical deep-dive, and situational questions — "
        "vary the type deliberately across the interview."
    ),
    "behavioral": (
        "BEHAVIORAL format only. Every main question MUST open with: "
        "'Tell me about a time when…' or 'Describe a situation where…'. "
        "Probe for Situation → Task → Action → Result with specific metrics, "
        "scope, and measurable outcomes. Reject vague generalities."
    ),
    "system_design": (
        "SYSTEM DESIGN format. Open broad ('Design a…', 'How would you architect…') "
        "then progressively drill into: scale requirements, component choices, "
        "data models, fault tolerance, latency/cost tradeoffs. "
        "Demand concrete decisions — not textbook definitions."
    ),
    "technical": (
        "TECHNICAL DEEP-DIVE format. Probe hands-on implementation details, "
        "debugging war stories, performance optimization, and production failure "
        "scenarios specific to the focus area. "
        "Reject surface-level answers — demand specifics and numbers."
    ),
    "leadership": (
        "LEADERSHIP & CULTURE format. Ask about people management, cross-functional "
        "influence, stakeholder alignment, strategic decisions under ambiguity, "
        "and team building. Reference Fortune 100 leadership expectations: "
        "Amazon Leadership Principles, Google's bar-raising culture, "
        "Microsoft's growth mindset, GCC enterprise governance."
    ),
}

# ── System prompts ────────────────────────────────────────────────────────────

_INTERVIEWER_SYSTEM = """\
You are a senior technical interviewer at a Fortune 100 company, specially Tech Companies \
Microsoft, Meta, Google, Amazon and GCC like GE, Shell, Johnson and Johnson, Bank of America, etc.

Role you are interviewing for: {role}
Focus areas: {domains}
Difficulty level: {difficulty}
Total distinct questions to ask: {num_questions}
Interview style: {style_instruction}

Rules:
- Ask exactly ONE question per turn. Never ask multiple questions in one message.
- After the candidate answers, either probe deeper with one follow-up OR move to the next distinct question.
- Be professional, direct, and concise — 2-4 sentences per interviewer turn max.
- Do NOT reveal any evaluation, scores, or feedback during the interview itself.
- After the candidate has answered all {num_questions} distinct questions, wrap up professionally in 2 sentences max.

CRITICAL — OUTPUT FORMAT: Begin EVERY response with exactly one of these tags on its own line:
[NEW QUESTION] — when introducing a brand-new distinct question
[FOLLOW-UP] — when probing deeper on the previous answer before moving to a new topic
These tags are stripped before the candidate sees your response. Never skip them.

Begin by introducing yourself in one sentence and immediately asking your first question.\
"""

_DEBRIEF_SYSTEM = """\
You are a technical interview evaluator. Based on the interview transcript, produce a structured debrief.

Use EXACTLY these ## headings — no additions, no reordering:

## Overall Impression
1-2 sentences on the candidate's overall performance and readiness for the role.

## Score
X / 10 — one-line justification.

## Strengths
3 bullet points referencing specific answers or moments from the transcript.

## Areas to Improve
3 bullet points with specific gaps or weak responses observed.

## Question-by-Question
For each main question asked (skip pure follow-ups), provide:
**Q:** [the question]
**Quality:** Strong / Adequate / Weak
**Feedback:** One sentence of specific feedback.

## Recommended Next Steps
2-3 specific, actionable prep steps for real interviews.

Be honest, specific, and constructive.\
"""


# ── Request models ────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    user_id: str
    role: str
    difficulty: str
    llm_provider: str = "gemini"
    num_questions: int = 5
    focus_area: str = ""
    interview_style: str = "mixed"


class ChatRequest(BaseModel):
    message: str


# ── Tag parsing helper ────────────────────────────────────────────────────────

def _parse_tag(text: str) -> tuple[str, str]:
    """
    Strip the [NEW QUESTION] or [FOLLOW-UP] prefix the LLM adds.
    Returns (tag, cleaned_text).
    If the AI forgets the tag, we leave count unchanged (safe default).
    """
    text = text.strip()
    if text.startswith("[NEW QUESTION]"):
        return "new_question", text[len("[NEW QUESTION]"):].strip()
    if text.startswith("[FOLLOW-UP]"):
        return "followup", text[len("[FOLLOW-UP]"):].strip()
    return "unknown", text


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/interview/start")
async def start_interview(req: StartRequest):
    role_info = settings.ROLES.get(req.role, {})
    role_label = role_info.get("label", req.role)
    domains_str = req.focus_area.strip() or "broad leadership topics relevant to the role"
    style_instruction = _STYLE_PROMPTS.get(req.interview_style, _STYLE_PROMPTS["mixed"])

    system = _INTERVIEWER_SYSTEM.format(
        role=role_label,
        domains=domains_str,
        difficulty=req.difficulty,
        num_questions=req.num_questions,
        style_instruction=style_instruction,
    )

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "id": session_id,
        "user_id": req.user_id,
        "role_label": role_label,
        "difficulty": req.difficulty,
        "interview_style": req.interview_style,
        "llm_provider": req.llm_provider,
        "num_questions": req.num_questions,
        "focus_area": domains_str,
        "system": system,
        "messages": [],
        "user_turns": 0,
        "main_question_count": 0,
        "is_complete": False,
    }

    # Write prompts to file for auditing
    _ROOT.joinpath("mock_prompt.md").write_text(
        f"# Mock Interview Prompts\n\n"
        f"## Session Config\n"
        f"- Role: {role_label}\n"
        f"- Difficulty: {req.difficulty}\n"
        f"- Style: {req.interview_style}\n"
        f"- Questions: {req.num_questions}\n"
        f"- Focus: {domains_str}\n"
        f"- Provider: {req.llm_provider}\n\n"
        f"---\n\n"
        f"## Interviewer System Prompt\n\n```\n{system}\n```\n\n"
        f"---\n\n"
        f"## Debrief System Prompt\n\n```\n{_DEBRIEF_SYSTEM}\n```\n",
        encoding="utf-8",
    )

    opening_raw = await _llm_turn(session_id)
    _, opening = _parse_tag(opening_raw)
    # Opening is always the first question
    _sessions[session_id]["main_question_count"] = 1
    _sessions[session_id]["messages"].append({"role": "assistant", "content": opening})

    return {
        "session_id": session_id,
        "opening": opening,
        "main_question_count": 1,
    }


@router.post("/interview/{session_id}/chat")
async def chat(session_id: str, req: ChatRequest):
    sess = _sessions.get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    if sess["is_complete"]:
        raise HTTPException(400, "Interview already complete")

    sess["messages"].append({"role": "user", "content": req.message})
    sess["user_turns"] += 1

    ai_raw = await _llm_turn(session_id)
    tag, ai_clean = _parse_tag(ai_raw)

    if tag == "new_question":
        sess["main_question_count"] += 1

    sess["messages"].append({"role": "assistant", "content": ai_clean})

    # Complete when user has answered enough AND AI has asked enough distinct questions.
    # Failsafe: also complete if user_turns reaches 1.5× num_questions (handles missed tags).
    n = sess["num_questions"]
    is_complete = (
        sess["user_turns"] >= n
        and (sess["main_question_count"] >= n or sess["user_turns"] >= int(n * 1.5))
    )
    sess["is_complete"] = is_complete

    return {
        "response": ai_clean,
        "is_complete": is_complete,
        "user_turns": sess["user_turns"],
        "main_question_count": sess["main_question_count"],
    }


@router.post("/interview/{session_id}/end")
async def end_interview(session_id: str):
    sess = _sessions.get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")

    transcript = "\n\n".join(
        f"**{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}:** {m['content']}"
        for m in sess["messages"]
    )

    prompt = (
        f"Interview for: {sess['role_label']}\n"
        f"Style: {sess['interview_style']}\n"
        f"Difficulty: {sess['difficulty']}\n"
        f"Focus: {sess['focus_area']}\n\n"
        f"TRANSCRIPT:\n\n{transcript}\n\n"
        f"Produce the structured debrief now."
    )

    from backend.llm import call_llm
    debrief = await call_llm(sess["llm_provider"], prompt, _DEBRIEF_SYSTEM)

    result = {
        "session_id": session_id,
        "role": sess["role_label"],
        "difficulty": sess["difficulty"],
        "num_questions": sess["num_questions"],
        "debrief": debrief,
    }
    _sessions.pop(session_id, None)  # free memory after debrief is returned
    return result


# ── LLM multi-turn call ───────────────────────────────────────────────────────

async def _llm_turn(session_id: str) -> str:
    sess = _sessions[session_id]
    provider = sess["llm_provider"]
    system = sess["system"]
    messages = sess["messages"]
    provider_cfg = settings.LLM_PROVIDERS.get(provider, {})

    if provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        model = provider_cfg.get("model", "gemini-2.0-flash")
        max_tokens = provider_cfg.get("max_tokens", 4000)

        contents = []
        # Gemini requires contents to begin with a user role
        if not messages or messages[0]["role"] == "assistant":
            contents.append(
                types.Content(role="user", parts=[types.Part(text="Begin the interview.")])
            )
        for msg in messages:
            g_role = "model" if msg["role"] == "assistant" else "user"
            contents.append(types.Content(role=g_role, parts=[types.Part(text=msg["content"])]))

        def _sync():
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                ),
            )

        resp = await asyncio.to_thread(_sync)
        return resp.text

    elif provider == "claude":
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        model = provider_cfg.get("model", "claude-sonnet-4-6")
        max_tokens = provider_cfg.get("max_tokens", 4000)

        claude_msgs = []
        if not messages or messages[0]["role"] == "assistant":
            claude_msgs.append({"role": "user", "content": "Begin the interview."})
        for msg in messages:
            role = "assistant" if msg["role"] == "assistant" else "user"
            claude_msgs.append({"role": role, "content": msg["content"]})

        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=claude_msgs,
        )
        return resp.content[0].text

    raise ValueError(f"Unsupported provider: {provider}")
