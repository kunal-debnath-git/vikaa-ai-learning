import json
import asyncio
import random
from pathlib import Path
from typing import Dict, List, Optional
from backend.llm import call_llm
from backend.config import settings

BANK_PATH = Path(__file__).parent / "question_bank.json"

# ── System Prompts ─────────────────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are an elite technical interview designer for Fortune 100 companies.
Your questions target senior leadership roles: Principal Architect, Director of Data Engineering, Head of AI.

DESIGN PHILOSOPHY:
- Leadership Thinking: Focus on architecture decision-making, trade-offs, scalability, and real-world problem solving.
- Trade-off Analysis: Ability to defend architectural decisions under constraints (cost vs performance vs scalability).
- NO RECALL: NO QUESTION on syntax, definitions, or "what is X".
- SCENARIO-DRIVEN: Every question sets a real-world business context.
- AMBIGUITY: Scenarios should have slight ambiguity requiring leadership judgment.

MARKET INTELLIGENCE LAYER:
Incorporate these recent trends and patterns: {trends}

Return ONLY valid JSON — no markdown, no preamble."""

ADAPTIVE_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + """

ADAPTIVE LEARNING DIRECTIVE:
This user has demonstrated weakness in the following areas (prioritise these heavily):
{weak_areas}

Generate questions specifically targeting these weak areas to accelerate improvement.
For strong areas, include only 1-2 consolidation questions."""


# ── Question Bank ──────────────────────────────────────────────────────────────

def load_bank() -> List[dict]:
    if BANK_PATH.exists():
        with open(BANK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_to_bank(question: dict) -> int:
    bank = load_bank()
    bank.append(question)
    with open(BANK_PATH, "w", encoding="utf-8") as f:
        json.dump(bank, f, indent=2, ensure_ascii=False)
    return len(bank)


def filter_bank(categories: Dict[str, List[str]], difficulty: str) -> List[dict]:
    results = [
        q for q in load_bank()
        if q.get("category") in categories
        and q.get("subcategory") in categories.get(q.get("category", ""), [])
        and q.get("difficulty") == difficulty
    ]
    random.shuffle(results)
    return results


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def build_question_prompt(
    role: str,
    difficulty: str,
    categories: Dict[str, List[str]],
    count: int,
    already_used_topics: List[str] = [],
    focus_areas: List[str] = []
) -> str:
    role_info = settings.ROLES.get(role, {})
    role_label = role_info.get("label", role)
    role_desc = role_info.get("description", "")

    flat_topics = [
        f"{cat} > {sub}"
        for cat, subcats in categories.items()
        for sub in subcats
    ]

    avoid_str = (
        f"\nAvoid repeating these topics already covered: {', '.join(already_used_topics[:10])}"
        if already_used_topics else ""
    )
    focus_str = (
        f"\nPRIORITY FOCUS (user weak areas — weight heavily): {', '.join(focus_areas)}"
        if focus_areas else ""
    )

    return f"""Generate exactly {count} high-impact, leadership-level scenario multiple-choice questions for:

TARGET ROLE: {role_label}
ROLE CONTEXT: {role_desc}
DIFFICULTY: {difficulty}
TOPICS TO SYNTHESIZE: {json.dumps(flat_topics)}
{avoid_str}{focus_str}

GOAL-AWARE GENERATION:
1. System design under constraints.
2. Long-term maintainability and FinOps.
3. Governance and Security in Enterprise ecosystems.
4. "What would you do as the architect?" perspective.

Each question MUST follow this structure:
{{
  "question_number": <int>,
  "category": "<parent category>",
  "subcategory": "<specific sub-topic>",
  "question_text": "<Detailed scenario — minimum 3-4 sentences + the strategic question>",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct_answer": "<A|B|C|D>",
  "explanation": "<3-sentence deep dive into WHY — reference trade-offs>",
  "learning_guidance": "<Targeted improvement path for this domain.>"
}}

Return a JSON array of {count} questions."""


# ── LLM Retry ──────────────────────────────────────────────────────────────────

async def _call_with_retry(provider: str, prompt: str, system_prompt: str, retries: int = 2) -> str:
    last_err: Exception = RuntimeError("Unknown error")
    for attempt in range(retries + 1):
        try:
            return await call_llm(provider=provider, prompt=prompt, system_prompt=system_prompt)
        except Exception as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
    raise last_err


# ── Core LLM Batch Generator ───────────────────────────────────────────────────

async def _llm_batch_generate(
    role: str,
    difficulty: str,
    categories: Dict[str, List[str]],
    llm_provider: str,
    total: int,
    system_prompt: str,
    focus_areas: List[str] = []
) -> List[dict]:
    if total <= 0:
        return []

    all_questions: List[dict] = []
    batch_size = 5
    used_topics: List[str] = []

    for _ in range(total // batch_size):
        prompt = build_question_prompt(
            role, difficulty, categories, batch_size,
            already_used_topics=used_topics, focus_areas=focus_areas
        )
        raw = await _call_with_retry(llm_provider, prompt, system_prompt)
        parsed = _parse_questions(raw)
        all_questions.extend(parsed)
        used_topics.extend(q.get("subcategory", "") for q in parsed)

    remainder = total % batch_size
    if remainder > 0:
        prompt = build_question_prompt(
            role, difficulty, categories, remainder,
            already_used_topics=used_topics, focus_areas=focus_areas
        )
        raw = await _call_with_retry(llm_provider, prompt, system_prompt)
        all_questions.extend(_parse_questions(raw))

    return all_questions


# ── Public Entry Point ─────────────────────────────────────────────────────────

async def generate_questions(
    role: str,
    difficulty: str,
    categories: Dict[str, List[str]],
    llm_provider: str,
    brain_mode: str = "llm",
    user_performance: Optional[List[dict]] = None,
    pre_loaded_questions: Optional[List[dict]] = None,
    total: int = 20
) -> List[dict]:

    mi = settings.config.get("market_intelligence", {})
    trends = ", ".join(mi.get("current_trends", []))

    # Spaced-repetition questions fill first slots
    pre_loaded = [
        {k: v for k, v in q.items() if k not in ("id", "session_id", "created_at")}
        for q in (pre_loaded_questions or [])
    ]
    remaining = max(0, total - len(pre_loaded))

    if remaining > 0:
        if brain_mode == "adaptive":
            generated = await _mode_adaptive(
                role, difficulty, categories, llm_provider,
                user_performance or [], trends, remaining
            )
        elif brain_mode == "bank":
            generated = await _mode_bank(
                role, difficulty, categories, llm_provider, trends, remaining
            )
        else:
            system_prompt = BASE_SYSTEM_PROMPT.format(trends=trends)
            generated = await _llm_batch_generate(
                role, difficulty, categories, llm_provider, remaining, system_prompt
            )
    else:
        generated = []

    all_questions = pre_loaded + generated
    for i, q in enumerate(all_questions):
        q["question_number"] = i + 1

    return all_questions


# ── Mode 1: Adaptive ───────────────────────────────────────────────────────────

async def _mode_adaptive(
    role, difficulty, categories, llm_provider,
    user_performance: List[dict], trends: str, total: int
) -> List[dict]:
    weak, focus_areas = [], []
    for p in user_performance:
        attempted = p.get("total_attempted", 0)
        if attempted == 0:
            continue
        accuracy = p["total_correct"] / attempted
        if accuracy < 0.70:
            weak.append(f"{p['category']} › {p.get('subcategory', '')} ({round(accuracy * 100)}% accuracy)")
            sub = p.get("subcategory", "").strip()
            if sub:
                focus_areas.append(sub)

    if weak:
        weak_str = "\n".join(f"  • {w}" for w in weak[:8])
        system_prompt = ADAPTIVE_SYSTEM_PROMPT.format(trends=trends, weak_areas=weak_str)
    else:
        system_prompt = BASE_SYSTEM_PROMPT.format(trends=trends) + \
            "\n\nThis user is performing well. Generate challenging consolidation questions."

    return await _llm_batch_generate(
        role, difficulty, categories, llm_provider, total,
        system_prompt, focus_areas[:5]
    )


# ── Mode 2: Question Bank ──────────────────────────────────────────────────────

async def _mode_bank(
    role, difficulty, categories, llm_provider, trends: str, total: int
) -> List[dict]:
    bank_questions = filter_bank(categories, difficulty)

    if len(bank_questions) >= total:
        return bank_questions[:total]

    remainder = total - len(bank_questions)
    system_prompt = BASE_SYSTEM_PROMPT.format(trends=trends)
    llm_questions = await _llm_batch_generate(
        role, difficulty, categories, llm_provider, remainder, system_prompt
    )
    return bank_questions + llm_questions


# ── JSON Parser ────────────────────────────────────────────────────────────────

def _parse_questions(raw_text: str) -> List[dict]:
    import re
    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
        text = text.strip()

    try:
        data = json.loads(text)
        return data if isinstance(data, list) else data.get("questions", [])
    except json.JSONDecodeError:
        pass

    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Failed to parse LLM JSON output. First 500 chars: {text[:500]}")
