import json
import random
from typing import Dict, List
from backend.llm import call_llm
from backend.config import settings


SYSTEM_PROMPT = """You are an elite technical interview designer for Fortune 100 companies.
Your questions target senior leadership roles: Principal Architect, Director of Data Engineering, Head of AI.

DESIGN PHILOSOPHY:
- Leadership Thinking: Focus on architecture decision-making, trade-offs, scalability, and real-world problem solving.
- Trade-off Analysis: Ability to defend architectural decisions under constraints (cost vs performance vs scalability).
- NO RECALL: NO QUESTION on syntax, definitions, or "what is X".
- SCENARIO-DRIVEN: Every question sets a real-world business context (e.g., "You are the Lead Architect at a global retail firm...").
- AMBIGUITY: Scenarios should have slight ambiguity requiring leadership judgment.

MARKET INTELLIGENCE LAYER:
Incorporate these recent trends and patterns: {trends}

Return ONLY valid JSON — no markdown, no preamble."""


def build_question_prompt(
    role: str,
    difficulty: str,
    categories: Dict[str, List[str]],
    count: int,
    already_used_topics: List[str] = []
) -> str:
    role_info = settings.ROLES.get(role, {})
    role_label = role_info.get("label", role)
    role_desc = role_info.get("description", "")

    # Flatten selected subcategories
    flat_topics = []
    for cat, subcats in categories.items():
        for sub in subcats:
            flat_topics.append(f"{cat} > {sub}")

    avoid_str = ""
    if already_used_topics:
        avoid_str = f"\nAvoid repeating these topics already covered: {', '.join(already_used_topics[:10])}"

    return f"""Generate exactly {count} high-impact, leadership-level scenario multiple-choice questions for:

TARGET ROLE: {role_label}
ROLE CONTEXT: {role_desc}
DIFFICULTY: {difficulty}
TOPICS TO SYNTHESIZE: {json.dumps(flat_topics)}
{avoid_str}

GOAL-AWARE GENERATION:
Questions must align with:
1. System design under constraints.
2. Long-term maintainability and FinOps.
3. Governance and Security in Enterprise ecosystems.
4. "What would you do as the architect?" perspective.

Each question MUST follow this structure:
{{
  "question_number": <int>,
  "category": "<parent category>",
  "subcategory": "<specific sub-topic>",
  "question_text": "<Detailed scenario — minimum 3-4 sentences setting context + the strategic question>",
  "options": {{
    "A": "<Plausible leadership decision>",
    "B": "<Plausible but sub-optimal architecture decision>",
    "C": "<Strategic and superior architectural choice>",
    "D": "<Cost-effective but risky alternative>"
  }},
  "correct_answer": "<A|B|C|D>",
  "explanation": "<Deep dive (3 sentences) into WHY this is the superior leadership choice, referencing specific trade-offs like Latency vs. Cost or Security vs. Flexibility.>",
  "learning_guidance": "<Targeted improvement path for this leadership domain.>"
}}

Return a JSON array of {count} questions."""


async def generate_questions(
    role: str,
    difficulty: str,
    categories: Dict[str, List[str]],
    llm_provider: str,
    total: int = 20
) -> List[dict]:
    all_questions = []
    batch_size = 5
    batches = total // batch_size
    remainder = total % batch_size
    used_topics: List[str] = []
    
    # Get Market Intel trends
    mi = settings.config.get("market_intelligence", {})
    trends = ", ".join(mi.get("current_trends", []))

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
            system_prompt=SYSTEM_PROMPT.format(trends=trends)
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
            system_prompt=SYSTEM_PROMPT.format(trends=trends)
        )
        parsed = _parse_questions(raw, offset=len(all_questions))
        all_questions.extend(parsed)

    # Final Sequential Renumbering
    for i, q in enumerate(all_questions):
        q["question_number"] = i + 1

    return all_questions


def _parse_questions(raw_text: str, offset: int = 0) -> List[dict]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Find start and end of JSON
        start_idx = -1
        end_idx = -1
        for i, line in enumerate(lines):
            if "[" in line and start_idx == -1: start_idx = i
            if "]" in line: end_idx = i
        if start_idx != -1 and end_idx != -1:
            text = "\n".join(lines[start_idx:end_idx+1])
        else:
            text = "\n".join(lines[1:-1])

    try:
        data = json.loads(text)
        return data if isinstance(data, list) else data.get("questions", [])
    except Exception as e:
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
        raise ValueError(f"Failed to parse LLM JSON output: {e}")
