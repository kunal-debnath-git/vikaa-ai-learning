from fastapi import APIRouter
from pydantic import BaseModel
from backend.llm import call_llm, call_llm_with_search
import asyncio, pathlib
from datetime import datetime, timezone

router = APIRouter()

REQUIREMENT_SYSTEM_PROMPT = """You are a senior technical interview coach specializing in Data, Cloud, and GenAI roles at Fortune 100 companies.

Given a main topic, sub-topic, and the candidate's personal context, produce a structured technical brief covering everything needed to discuss this feature confidently in an interview.

Structure your output exactly as follows:

## What Is It
2-3 sentence technical definition. No fluff.

## When & Why You'd Use It
2-3 concrete enterprise use cases with business context.

## How It Works (Key Mechanics)
Core internals / architecture as bullet points. Interview-depth, not textbook-depth.

## Pros & Trade-offs
Honest assessment — what makes it great, where it struggles, when NOT to use it.

## Common Gotchas & Failure Modes
Things that trip up teams in production. Mistakes interviewers love to probe.

## Interview Angles
How interviewers typically surface this topic. What follow-up questions to expect.

Be sharp, practical, and opinionated — not a documentation page."""

RESPONSE_SYSTEM_PROMPT = """You are a senior technical interview coach helping a candidate speak confidently about a technology they may not have deep hands-on experience with.

Using the technical brief and the candidate's personal context, synthesize a polished interview-ready study card.

Structure your output exactly as follows:

## 30-Second Opener
A crisp 1-2 sentence intro the candidate can say naturally to establish familiarity.

## My Angle / Story Hook
A realistic narrative framing built from the candidate's context. Frame adjacent experience confidently even if they haven't used it directly.

## Key Talking Points
5-7 bullet points to internalize. Specific enough to sound experienced, not textbook-generic.

## If They Dig Deeper
3-4 likely follow-up questions with concise confident answers. Use EXACTLY this format for each pair — each on its own line with a blank line between pairs:

**Q:** [the follow-up question]

**A:** [concise confident answer]

## The Line That Impresses
One specific insight, trade-off observation, or nuanced opinion that signals senior-level thinking.

Write in first-person where natural. Be specific and confident."""

RECOMMENDATIONS_SYSTEM_PROMPT = """You are a senior technical advisor. Use Google Search to find the most recent features, announcements, and updates for the given topic and sub-topic.

Structure your output exactly as follows:

## What's New
1-sentence summary of where this product area is heading right now, based on search results.

## Recent Features & Updates
- **[Feature Name]** *(Month Year)*: What it does and why it matters for enterprise Data/Cloud/AI teams.
(List 4-6 items, newest first. Use accurate dates from search results. Flag GA vs Preview/Beta.)

## Why It Matters in Interviews
1-2 sentences on why knowing these updates signals senior-level awareness to an interviewer.

Be accurate and specific. Pull real release dates from search results, not estimates."""


class DukRequest(BaseModel):
    main_topic: str
    sub_topic: str
    user_context: str = ""
    llm_provider: str = "gemini"


@router.post("/duk/generate")
async def generate_duk(req: DukRequest):
    root = pathlib.Path(__file__).parent.parent.parent

    # Step 1: technical brief
    req_user_prompt = (
        f"Main Topic: {req.main_topic}\n"
        f"Sub Topic: {req.sub_topic}\n"
        f"Candidate Context: {req.user_context or 'No specific context provided — generate general interview prep.'}\n\n"
        f"Generate the structured technical brief for this topic."
    )
    (root / "requirement_prompt.md").write_text(
        f"# Requirement Prompt\n\n## System\n\n{REQUIREMENT_SYSTEM_PROMPT}\n\n---\n\n## User\n\n{req_user_prompt}",
        encoding="utf-8"
    )
    brief = await call_llm(req.llm_provider, req_user_prompt, REQUIREMENT_SYSTEM_PROMPT)

    # Step 2: interview card + recommendations in parallel
    res_user_prompt = (
        f"Topic: {req.main_topic} → {req.sub_topic}\n\n"
        f"Candidate's Personal Context:\n{req.user_context or 'No specific context provided.'}\n\n"
        f"Technical Brief:\n{brief}\n\n"
        f"Now generate the interview-ready study card."
    )
    (root / "response_prompt.md").write_text(
        f"# Response Prompt\n\n## System\n\n{RESPONSE_SYSTEM_PROMPT}\n\n---\n\n## User\n\n{res_user_prompt}",
        encoding="utf-8"
    )

    rec_user_prompt = (
        f"Search for the latest features, announcements, and release notes for: "
        f"{req.main_topic} — {req.sub_topic}. "
        f"What has been released or announced most recently? Focus on what enterprise Data and Cloud teams care about."
    )

    searched_at = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    card, recommendations = await asyncio.gather(
        call_llm(req.llm_provider, res_user_prompt, RESPONSE_SYSTEM_PROMPT),
        call_llm_with_search(rec_user_prompt, RECOMMENDATIONS_SYSTEM_PROMPT),
    )

    return {
        "main_topic": req.main_topic,
        "sub_topic": req.sub_topic,
        "brief": brief,
        "card": card,
        "recommendations": recommendations,
        "searched_at": searched_at,
    }
