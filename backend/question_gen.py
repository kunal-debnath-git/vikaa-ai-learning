import json
import asyncio
import random
from pathlib import Path
from typing import Dict, List, Optional
from backend.llm import call_llm
from backend.config import settings

BANK_PATH = Path(__file__).parent / "question_bank.json"

# ── System Prompts ─────────────────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are an elite technical interview architect and knowledge coach for Fortune 100 technology and data leadership hiring.

YOUR MANDATE:
Design MCQs that measure DECISION-MAKING QUALITY and reinforce architectural thinking for a senior practitioner brushing up for Lead Data & AI Architect through CTO-level roles.
Every question tests: "Given this real-world constraint, which architectural decision is BEST and WHY?"
Every explanation must teach — not just validate. A candidate who got it wrong should walk away with a clear mental model they can apply immediately.

QUESTION DESIGN LAWS:
1. SCENARIO FIRST: Every question opens with a concrete business context — company scale, team size, regulatory pressure, or cost constraint. Minimum 3 sentences before the question.
2. NO RECALL: Zero questions on "what is X", syntax, definitions, or feature lists. All questions must require judgment.
3. OPTION INTEGRITY: All 4 options must be real architectural choices a senior engineer might genuinely propose. No straw-man distractors, no obviously absurd options.
4. OPTION DIFFERENTIATION: Options must differ on a specific architectural dimension — e.g., managed vs self-hosted, eventual vs strong consistency, cost vs latency, scalability vs simplicity. Make the trade-off axis explicit.
5. CORRECT ANSWER LOCK: The correct answer must be clearly superior BECAUSE OF the specific constraint stated in the scenario — not because it is generally "best practice". If you remove the scenario constraint, the answer should become debatable.
6. WRONG ANSWER SPECIFICITY: Each distractor must be wrong for a distinct, non-trivial reason. State those reasons in the explanation. A wrong answer that is "just less good" is not a valid distractor.
7. DIFFICULTY FIDELITY: Honour the difficulty calibration exactly. Do not soften Hard questions or over-engineer Easy ones.
8. WHEN-TO-APPLY THINKING: For architecture and strategy topics, the question must reveal WHEN to choose a pattern, not just HOW it works. The scenario constraints must be the deciding factor, not general preference.

MARKET INTELLIGENCE:
Incorporate these active enterprise patterns where relevant: {trends}

OUTPUT LENGTH LIMITS (hard constraints — exceeding these breaks parsing):
- question_text: maximum 60 words
- Options: exactly 4 (A, B, C, D only — no E or beyond), maximum 25 words each
- explanation: maximum 3 sentences
- learning_guidance: maximum 2 sentences

Return ONLY valid JSON — no markdown, no preamble, no text outside the JSON array."""

ADAPTIVE_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + """

ADAPTIVE LEARNING DIRECTIVE:
This user has demonstrated weakness in the following areas — weight these domains heavily (70%+ of questions):
{weak_areas}

For strong areas, include only consolidation questions with harder edge-case scenarios."""


# ── Role Perspective Map ───────────────────────────────────────────────────────

ROLE_PERSPECTIVES = {
    "cto": {
        "lens": (
            "Chief Data Architect / CTO: enterprise-wide data & AI platform strategy. "
            "Accountable for multi-cloud architecture, multi-team productivity, FinOps at scale, "
            "regulatory compliance, GenAI adoption, security posture, and talent strategy. "
            "Decisions affect hundreds of engineers, millions in budget, and board-level risk appetite."
        ),
        "question_style": (
            "Strategic platform decisions that span multiple domains simultaneously. "
            "Scenarios involve vendor selection, org-wide governance, build-vs-buy at scale, "
            "large-scale migration strategy, security & compliance trade-offs, "
            "or integrating data + AI + cloud in a single coherent platform. "
            "The question should reflect what a CTO presents to the board, defends to the CISO, "
            "or proposes in a pre-sales executive briefing."
        ),
        "cross_domain": True,
    },
    "architect": {
        "lens": (
            "Lead Data Solution Architect: end-to-end system design, enterprise architecture patterns, "
            "data governance, platform selection, migration planning, and cost-optimisation. "
            "Accountable for solution proposals, architecture decision records, and downstream consumer SLAs."
        ),
        "question_style": (
            "Architecture trade-off scenarios requiring platform selection, integration pattern choice, "
            "migration approach, or governance framework design. "
            "Include constraints: team maturity, SLA, compliance, budget, or existing estate. "
            "Pre-sales and proposal framing scenarios are also in scope — "
            "e.g., how to frame a solution for a client with mixed on-prem and cloud workloads."
        ),
        "cross_domain": False,
    },
    "engineer": {
        "lens": (
            "Lead Data Engineer: production-grade pipeline design, Spark/Delta performance, "
            "CI/CD for data, observability, and cost-efficient compute. "
            "Decisions affect pipeline SLAs, data quality, and on-call burden."
        ),
        "question_style": (
            "Technical implementation scenario requiring the optimal engineering approach "
            "for scalability, reliability, cost, or performance. Include specific scale numbers (TB, QPS, teams)."
        ),
        "cross_domain": False,
    },
    "ai_engineer": {
        "lens": (
            "Lead AI Engineer: productionizing LLMs and AI systems, RAG architecture, "
            "LLMOps, model serving, and GenAI infrastructure. "
            "Decisions affect inference latency, cost per query, and model reliability in production."
        ),
        "question_style": (
            "AI/ML system design and LLMOps scenarios requiring production-grade decisions. "
            "Include constraints: latency SLA, cost per call, data freshness, or compliance."
        ),
        "cross_domain": False,
    },
}

# ── Difficulty Calibration ─────────────────────────────────────────────────────

DIFFICULTY_CALIBRATION = {
    "Easy": (
        "EASY CALIBRATION: The correct answer should be clearly superior to a senior practitioner who knows the domain well. "
        "One option should be clearly best; the others should be plausible but each have a single, identifiable flaw "
        "(too expensive, operationally heavy, insecure, doesn't scale to the stated requirement). "
        "Scenario: single primary constraint to resolve. A well-prepared candidate should get this right."
    ),
    "Medium": (
        "MEDIUM CALIBRATION: Two options appear viable at first glance. "
        "The correct one wins because of a specific architectural reason tied to the scenario constraint. "
        "Requires the candidate to weigh one key trade-off (e.g., managed overhead vs vendor lock-in, "
        "latency vs cost, strong consistency vs availability). "
        "Scenario: 2–3 simultaneous constraints. Expect ~60% correct from a prepared candidate."
    ),
    "Hard": (
        "HARD CALIBRATION: Genuine architectural ambiguity — no obviously wrong option. "
        "All 4 options are defensible in SOME context. The correct one is optimal ONLY because of the "
        "combined intersection of 3+ constraints in this specific scenario. "
        "Scenario: complex real-world with competing priorities (cost + compliance + latency + team capability). "
        "Expect ~30-40% correct even from strong candidates."
    ),
}


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
    perspective = ROLE_PERSPECTIVES.get(role, ROLE_PERSPECTIVES["architect"])
    diff_guide = DIFFICULTY_CALIBRATION.get(difficulty, DIFFICULTY_CALIBRATION["Medium"])

    # Build per-category topic menu and proportional distribution
    cat_list = list(categories.keys())
    n_cats = len(cat_list)
    distribution: Dict[str, int] = {}
    if n_cats == 0:
        pass  # empty — distribution stays {}
    elif n_cats >= count:
        # More categories than slots: 1 question each for the first `count` categories
        for i, cat in enumerate(cat_list):
            distribution[cat] = 1 if i < count else 0
    else:
        base_per_cat = count // n_cats
        extra = count - base_per_cat * n_cats  # always 0 ≤ extra < n_cats
        for i, cat in enumerate(cat_list):
            distribution[cat] = base_per_cat + (1 if i < extra else 0)

    topic_menu_lines = []
    dist_lines = []
    for cat, subs in categories.items():
        topic_menu_lines.append(f'  "{cat}": {json.dumps(subs)}')
        dist_lines.append(f"  - {cat}: {distribution.get(cat, 1)} question(s) — draw from its subcategories above")

    topic_menu_str = "{\n" + ",\n".join(topic_menu_lines) + "\n}"
    dist_str_block = "\n".join(dist_lines)

    # Cross-domain synthesis hint for roles that span multiple domains
    cross_domain_str = ""
    if perspective["cross_domain"] and n_cats > 1:
        n_cross = max(1, count // 3)
        cross_domain_str = f"""
CROSS-DOMAIN SYNTHESIS REQUIREMENT (critical for this role):
At least {n_cross} of the {count} questions MUST combine 2 or more of the selected domains in a single scenario.
Example: a CTO scenario where a GenAI workload on Azure requires Data Governance and FinOps trade-offs forces
the cross-platform leadership thinking this role actually demands. Single-domain siloed questions are NOT sufficient
for this role.
"""

    avoid_str = (
        f"\nAVOID REPEATING: These subcategories were already covered — do not reuse them: {', '.join(already_used_topics[:12])}"
        if already_used_topics else ""
    )
    focus_str = (
        f"\nPRIORITY FOCUS — weight these subcategories heavily (user weak areas): {', '.join(focus_areas)}"
        if focus_areas else ""
    )

    return f"""Generate exactly {count} MCQs for the following specification. Follow every rule precisely.

━━━ ROLE ━━━
Title: {role_label}
Perspective: {perspective['lens']}
Question Style: {perspective['question_style']}

━━━ DIFFICULTY ━━━
Level: {difficulty}
{diff_guide}

━━━ TOPIC DISTRIBUTION (MANDATORY — do not deviate) ━━━
{dist_str_block}

━━━ TOPIC MENU (subcategories to draw from per category) ━━━
{topic_menu_str}
{avoid_str}{focus_str}{cross_domain_str}
━━━ OPTION QUALITY REQUIREMENTS (non-negotiable) ━━━
- All 4 options must be architecturally plausible proposals a real senior engineer would make.
- Options must differ on a SPECIFIC trade-off axis stated or implied in the scenario
  (e.g., managed vs self-hosted, cost vs latency, vendor lock-in vs operational simplicity).
- NEVER use: "do nothing", "ask the vendor", obviously broken syntax, or trivially absurd options.
- The correct answer must be the BEST choice specifically because of the constraint(s) in this scenario.
  Remove the constraint and the answer should become debatable — that is the quality bar.
- Every distractor must be wrong for a specific, nameable reason (too expensive at this scale,
  operationally unmanageable for this team size, violates the stated compliance requirement, etc.).

━━━ REQUIRED JSON STRUCTURE ━━━
Each object in the array must have exactly these fields:
{{
  "question_number": <int, 1-{count}>,
  "category": "<exact category name from the topic menu above>",
  "subcategory": "<exact subcategory name from the topic menu above>",
  "question_text": "<2-3 sentences max (under 75 words). State company type, scale, and ONE key constraint. End with the specific decision question.>",
  "options": {{
    "A": "<one sentence, under 30 words>",
    "B": "<one sentence, under 30 words>",
    "C": "<one sentence, under 30 words>",
    "D": "<one sentence, under 30 words>"
  }},
  "correct_answer": "<A|B|C|D>",
  "explanation": "<3 sentences max: (1) Why the correct answer wins given the specific constraint. (2) Why the strongest distractor fails for this scenario. (3) The mental model: When X condition exists, choose Y because Z.>",
  "learning_guidance": "<2 sentences max: The concept you likely confused and the named Azure service or pattern to review.>"
}}

Return a JSON array of exactly {count} objects. No markdown fences, no preamble, no text outside the JSON array."""


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

def _active_categories(
    categories: Dict[str, List[str]],
    used_subcats: List[str]
) -> Dict[str, List[str]]:
    """Return categories with already-used subcategories removed.
    Falls back to the full original dict if everything is exhausted."""
    active = {
        cat: [s for s in subs if s not in used_subcats]
        for cat, subs in categories.items()
    }
    active = {cat: subs for cat, subs in active.items() if subs}
    return active if active else categories  # fallback: reset when all exhausted


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

    batch_size = 2
    batch_sizes = [batch_size] * (total // batch_size)
    if total % batch_size:
        batch_sizes.append(total % batch_size)

    # Pre-assign different subcategory slices to each batch so parallel calls
    # cover different topics rather than all competing for the same subcategories.
    all_subs = [sub for subs in categories.values() for sub in subs]
    n = len(batch_sizes)
    slice_size = max(1, len(all_subs) // n) if n else 1

    async def _one_batch(count: int, batch_idx: int) -> List[dict]:
        avoid = all_subs[:batch_idx * slice_size]
        active = _active_categories(categories, avoid) if avoid else categories
        prompt = build_question_prompt(
            role, difficulty, active, count,
            already_used_topics=avoid[:12],
            focus_areas=focus_areas,
        )
        raw = await _call_with_retry(llm_provider, prompt, system_prompt)
        questions = _parse_questions(raw)
        # Salvage: if we got fewer than requested, that's still valid
        return questions if questions else []

    # return_exceptions=True: a single bad batch does not kill the whole gather
    results = await asyncio.gather(
        *[_one_batch(s, i) for i, s in enumerate(batch_sizes)],
        return_exceptions=True,
    )

    all_questions: List[dict] = []
    retry_tasks = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[question_gen] batch {i} failed ({type(result).__name__}), retrying with 1 question")
            retry_tasks.append(_one_batch(1, i))
        else:
            all_questions.extend(result)

    # Retry each failed batch with a single question (simpler, smaller output)
    if retry_tasks:
        retry_results = await asyncio.gather(*retry_tasks, return_exceptions=True)
        for result in retry_results:
            if not isinstance(result, Exception):
                all_questions.extend(result)

    if not all_questions:
        raise RuntimeError(
            f"All {len(batch_sizes)} LLM batches failed. "
            "Check API key, model availability, and token limits."
        )

    print(f"[question_gen] generated {len(all_questions)} questions")
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

BANK_CAP_PCT = 0.15  # local bank may contribute at most 15% of total questions

async def _mode_bank(
    role, difficulty, categories, llm_provider, trends: str, total: int
) -> List[dict]:
    bank_cap = int(total * BANK_CAP_PCT)  # e.g. 20 * 0.15 = 3
    bank_questions = filter_bank(categories, difficulty)[:bank_cap]

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

    # Try clean parse first
    try:
        data = json.loads(text)
        raw = data if isinstance(data, list) else data.get("questions", [])
        return _validate_questions(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting the array portion
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return _validate_questions(json.loads(match.group()))
        except json.JSONDecodeError:
            pass

    # Truncated JSON recovery: extract complete {...} objects, skipping } inside strings
    salvaged = []
    depth = 0
    start = None
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == '\\' and in_string:
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start:i + 1])
                    if isinstance(obj, dict) and "question_text" in obj:
                        salvaged.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None

    if salvaged:
        return _validate_questions(salvaged)

    raise ValueError(f"Failed to parse LLM JSON output. First 500 chars: {text[:500]}")


def _validate_questions(questions: List[dict]) -> List[dict]:
    valid = []
    required_keys = {"question_text", "options", "correct_answer"}
    valid_answers = {"A", "B", "C", "D"}
    for q in questions:
        if not required_keys.issubset(q.keys()):
            continue
        opts = q.get("options", {})
        if not isinstance(opts, dict) or not {"A", "B", "C", "D"}.issubset(opts.keys()):
            continue
        if q.get("correct_answer", "").strip().upper() not in valid_answers:
            continue
        # Trim options to A-D only
        q["options"] = {k: opts[k] for k in ["A", "B", "C", "D"]}
        q["correct_answer"] = q["correct_answer"].strip().upper()
        valid.append(q)
    return valid
