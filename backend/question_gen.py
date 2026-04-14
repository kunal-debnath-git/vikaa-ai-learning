import json
import random
from typing import Dict, List
from backend.llm import call_llm
from backend.config import settings


SYSTEM_PROMPT = """You are an elite technical interview designer for Fortune 100 companies.
Your questions target senior leadership roles: Principal Architect, Director of Data Engineering, Head of AI.

RULES (strictly follow):
1. Every question is SCENARIO-DRIVEN — set a real business context first.
2. NEVER ask about syntax, definitions, or "what is X".
3. Questions must require trade-off analysis, architectural judgement, or leadership decisions.
4. Wrong options must be plausible — an inexperienced architect might pick them.
5. The explanation must justify WHY the correct answer is architecturally superior.
6. Return ONLY valid JSON — no markdown, no preamble."""


def build_question_prompt(
    role: str,
    difficulty: str,
    categories: Dict[str, List[str]],
    count: int,
    already_used_topics: List[str] = []
) -> str:
    role_label = settings.ROLES.get(role, {}).get("label", role)
    role_desc = settings.ROLES.get(role, {}).get("description", "")

    # Flatten selected subcategories
    flat_topics = []
    for cat, subcats in categories.items():
        for sub in subcats:
            flat_topics.append(f"{cat} > {sub}")

    avoid_str = ""
    if already_used_topics:
        avoid_str = f"\nAvoid repeating these topics already covered: {', '.join(already_used_topics[:10])}"

    return f"""Generate exactly {count} scenario-based multiple-choice questions for this interview context:

ROLE: {role_label}
ROLE FOCUS: {role_desc}
DIFFICULTY: {difficulty}
TOPICS TO COVER (pick varied topics from this list): {json.dumps(flat_topics)}
{avoid_str}

Each question MUST follow this format:
{{
  "question_number": <int>,
  "category": "<parent category>",
  "subcategory": "<specific sub-topic>",
  "question_text": "<scenario setup + the question — minimum 3 sentences>",
  "options": {{
    "A": "<option text>",
    "B": "<option text>",
    "C": "<option text>",
    "D": "<option text>"
  }},
  "correct_answer": "<A|B|C|D>",
  "explanation": "<2-3 sentences explaining why this is architecturally superior, referencing real trade-offs>",
  "learning_guidance": "<2-3 sentences — what concept to study, why it matters for leadership roles>"
}}

Return a JSON array of {count} questions. ONLY return the JSON array, nothing else."""


async def generate_questions(
    role: str,
    difficulty: str,
    categories: Dict[str, List[str]],
    llm_provider: str,
    total: int = 20
) -> List[dict]:
    """
    Generate questions in batches of 5 to avoid token limits and ensure quality.
    Returns list of parsed question dicts.
    """
    all_questions = []
    batch_size = 5
    batches = total // batch_size
    remainder = total % batch_size
    used_topics: List[str] = []

    for i in range(batches):
        prompt = build_question_prompt(
            role=role,
            difficulty=difficulty,
            categories=categories,
            count=batch_size,
            already_used_topics=used_topics
        )
        raw = await call_llm(
            provider=llm_provider,
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT
        )
        parsed = _parse_questions(raw, offset=len(all_questions))
        all_questions.extend(parsed)
        used_topics.extend([q.get("subcategory", "") for q in parsed])

    if remainder > 0:
        prompt = build_question_prompt(
            role=role,
            difficulty=difficulty,
            categories=categories,
            count=remainder,
            already_used_topics=used_topics
        )
        raw = await call_llm(
            provider=llm_provider,
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT
        )
        parsed = _parse_questions(raw, offset=len(all_questions))
        all_questions.extend(parsed)

    # Re-number sequentially
    for i, q in enumerate(all_questions):
        q["question_number"] = i + 1

    return all_questions


def _parse_questions(raw_text: str, offset: int = 0) -> List[dict]:
    """Parse LLM response into list of question dicts."""
    # Strip markdown fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        questions = json.loads(text)
        if isinstance(questions, dict) and "questions" in questions:
            questions = questions["questions"]
        return questions if isinstance(questions, list) else []
    except json.JSONDecodeError as e:
        # Try to extract JSON array from text
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        raise ValueError(f"Could not parse LLM response as JSON: {e}\nRaw: {text[:500]}")
