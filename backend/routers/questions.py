import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.db import tbl, bypass_session
from backend.config import settings
from backend.question_gen import generate_questions, save_to_bank

router = APIRouter(tags=["questions"])

BANK_PATH = Path(__file__).parent.parent / "question_bank.json"


# ── Spaced Repetition Helper ───────────────────────────────────────────────────

async def _get_spaced_rep_questions(user_id: str, role: str, difficulty: str, limit: int = 5) -> List[dict]:
    """Return questions the user got wrong in their last 3 sessions (same role + difficulty)."""
    sessions_resp = tbl("sessions").select("id").eq(
        "user_id", user_id
    ).eq("role", role).eq("difficulty", difficulty).eq(
        "completed", True
    ).order("started_at", desc=True).limit(3).execute()

    if not sessions_resp.data:
        return []

    session_ids = [s["id"] for s in sessions_resp.data]

    answers_resp = tbl("answers").select("question_id").in_(
        "session_id", session_ids
    ).eq("is_correct", False).execute()

    if not answers_resp.data:
        return []

    q_ids = list({a["question_id"] for a in answers_resp.data})[:limit * 2]

    questions_resp = tbl("questions").select(
        "question_number, category, subcategory, question_text, options, correct_answer, explanation, learning_guidance"
    ).in_("id", q_ids).limit(limit).execute()

    return questions_resp.data or []


# ── Generate ───────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/generate")
async def generate_session_questions(session_id: str):
    # BYPASS FOR TESTING
    if session_id == "11111111-1111-1111-1111-111111111111":
        return {"status": "success", "count": 20, "mode": "bypass"}

    session_resp = tbl("sessions").select("*").eq("id", session_id).execute()
    if not session_resp.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_resp.data[0]
    brain_mode = session.get("brain_mode", "llm")

    # Fetch user's performance data for adaptive mode
    user_performance = []
    if brain_mode == "adaptive":
        perf_resp = tbl("performance_tracking").select("*").eq(
            "user_id", session["user_id"]
        ).execute()
        user_performance = perf_resp.data or []

    # Fetch spaced repetition questions (wrong answers from last 3 sessions)
    spaced_questions = await _get_spaced_rep_questions(
        user_id=session["user_id"],
        role=session["role"],
        difficulty=session["difficulty"],
    )

    questions = await generate_questions(
        role=session["role"],
        difficulty=session["difficulty"],
        categories=session["categories"],
        llm_provider=session["llm_provider"],
        brain_mode=brain_mode,
        user_performance=user_performance,
        pre_loaded_questions=spaced_questions,
        total=session.get("total_questions", 20),
    )

    for q in questions:
        q["session_id"] = session_id
        tbl("questions").insert(q).execute()

    return {"status": "success", "count": len(questions)}


# ── Get Questions ──────────────────────────────────────────────────────────────

_BYPASS_QUESTION_TEMPLATES = [
    {
        "category": "Cloud Platforms", "subcategory": "Azure (General)",
        "question_text": "TEST MODE Q{n} — You are Lead Architect at a global retail firm migrating to Azure. The CTO demands zero downtime, full RBAC, and a 30% cost reduction in Year 1. Which approach is architecturally superior?",
        "options": {"A": "Lift-and-shift all VMs to Azure IaaS immediately", "B": "Multi-region Active-Active with Traffic Manager, Right-size with Azure Advisor, RBAC via Entra ID with PIM", "C": "On-premise hybrid with Azure Arc management only", "D": "Migrate to a single Azure region to minimise latency"},
        "correct_answer": "B",
        "explanation": "Multi-region Active-Active satisfies zero-downtime and resilience. Azure Advisor right-sizing achieves cost reduction. PIM enforces just-in-time RBAC.",
        "learning_guidance": "Study Azure Traffic Manager routing policies, Azure Advisor cost recommendations, and PIM for zero-standing-privilege access."
    },
    {
        "category": "Data Architecture", "subcategory": "Medallion Architecture (Bronze/Silver/Gold)",
        "question_text": "TEST MODE Q{n} — A financial client needs real-time fraud detection on streaming transactions alongside daily batch reporting. Which Medallion Architecture variant best satisfies both?",
        "options": {"A": "Bronze batch ingestion only, with Gold summaries for reports", "B": "Lambda architecture with separate speed/batch layers feeding Silver", "C": "Unified streaming Bronze layer using Delta Lake with DLT, materialized Silver for ML, Gold for BI", "D": "Direct Kafka to Gold, bypassing Silver for low latency"},
        "correct_answer": "C",
        "explanation": "Delta Lake + DLT unifies streaming and batch in one Bronze layer. Silver materialises ML features; Gold serves BI. This avoids Lambda complexity while meeting both SLAs.",
        "learning_guidance": "Study Delta Live Tables streaming ingestion, Auto Loader, and medallion layer SLA contracts."
    },
    {
        "category": "Data Engineering", "subcategory": "PySpark & Spark Optimization (Data Skew, Shuffle Tuning)",
        "question_text": "TEST MODE Q{n} — A PySpark job joining a 5 TB fact table with a 200 MB dimension consistently spills to disk and runs 40 min. What is the most impactful single optimisation?",
        "options": {"A": "Increase driver memory to 64 GB", "B": "Broadcast join the dimension table to eliminate shuffle", "C": "Partition the fact table by month and repartition to 2000", "D": "Enable Adaptive Query Execution with spark.sql.adaptive.enabled=true"},
        "correct_answer": "B",
        "explanation": "Broadcasting a sub-300 MB table removes the shuffle entirely — the most impactful fix. AQE helps but cannot eliminate shuffle for a large-to-large join.",
        "learning_guidance": "Study broadcast join thresholds (spark.sql.autoBroadcastJoinThreshold), AQE skew hints, and salting for data skew."
    },
    {
        "category": "Generative AI & AI Stack", "subcategory": "RAG – All Patterns (Naive, Advanced, Agentic)",
        "question_text": "TEST MODE Q{n} — An enterprise knowledge base returns irrelevant chunks for multi-hop questions (e.g. 'What is our policy on X given the Y regulation?'). Which RAG pattern addresses this?",
        "options": {"A": "Naive RAG with larger chunk sizes", "B": "HyDE (Hypothetical Document Embeddings) with MMR re-ranking", "C": "Agentic RAG with a query-decomposition agent issuing sub-queries per hop", "D": "Increase top-K retrieval from 5 to 20"},
        "correct_answer": "C",
        "explanation": "Agentic RAG decomposes multi-hop questions into atomic sub-queries, retrieves and synthesises each hop independently — solving the cross-reference problem naive RAG cannot.",
        "learning_guidance": "Study LangGraph multi-hop agent patterns, LlamaIndex sub-question query engine, and FLARE iterative retrieval."
    },
    {
        "category": "Claude & Anthropic Stack", "subcategory": "Claude API & Prompt Engineering",
        "question_text": "TEST MODE Q{n} — You need Claude to reliably output JSON for a downstream parser. What is the most robust approach?",
        "options": {"A": "Ask Claude to 'respond only in JSON' in the system prompt", "B": "Use tool_use / function calling to enforce a typed schema via the API", "C": "Post-process the response with regex to extract JSON", "D": "Set temperature=0 and ask for JSON in the user message"},
        "correct_answer": "B",
        "explanation": "Tool use forces Claude to emit structured output conforming to the defined JSON schema — the only approach with API-level enforcement. Prompt instructions alone can fail on edge cases.",
        "learning_guidance": "Study Anthropic tool_use parameter, input_schema definition, and the structured output pattern in Claude docs."
    },
    {
        "category": "Core Data Platform", "subcategory": "Unity Catalog",
        "question_text": "TEST MODE Q{n} — A data platform team wants row-level security on a Delta table so analysts only see their own region's data. Which Unity Catalog feature implements this with least operational overhead?",
        "options": {"A": "Create separate Delta tables per region and grant SELECT per group", "B": "Use Unity Catalog Row Filters with a SQL policy function bound to current_user()", "C": "Apply Spark dynamic partition pruning in each query", "D": "Implement VIEWs per region and revoke access to base tables"},
        "correct_answer": "B",
        "explanation": "Row Filters in Unity Catalog apply a policy function transparently at query time — no table proliferation or per-query logic needed. It's the native, least-overhead approach.",
        "learning_guidance": "Study Unity Catalog Row Filters, Column Masks, and GRANT/REVOKE on Delta tables at catalog.schema.table level."
    },
    {
        "category": "Data Architecture", "subcategory": "FinOps & Cost Optimization",
        "question_text": "TEST MODE Q{n} — A Databricks cluster is running all-purpose clusters 24/7 for ETL pipelines. What is the primary FinOps action to reduce cost?",
        "options": {"A": "Upgrade to a larger instance type for faster completion", "B": "Migrate ETL workloads to automated job clusters with auto-termination", "C": "Enable Photon engine on all-purpose clusters", "D": "Add more workers to reduce wall-clock time"},
        "correct_answer": "B",
        "explanation": "Job clusters spin up for a run and terminate automatically — paying only for execution time. All-purpose clusters billed for idle time are the #1 Databricks cost waste.",
        "learning_guidance": "Study Databricks job cluster vs all-purpose cluster pricing, auto-termination settings, and Spot/preemptible instance policies."
    },
    {
        "category": "Cloud Platforms", "subcategory": "Azure Networking & Security",
        "question_text": "TEST MODE Q{n} — An ADF pipeline must access an Azure SQL Database without exposing it to the public internet. What is the correct architecture?",
        "options": {"A": "Allow Azure services to access the SQL firewall rule", "B": "Use a Self-Hosted Integration Runtime in the same VNet as the SQL Private Endpoint", "C": "Whitelist the ADF IP ranges in the SQL firewall", "D": "Enable Managed VNet on ADF and use a Managed Private Endpoint to SQL"},
        "correct_answer": "D",
        "explanation": "ADF Managed VNet with Managed Private Endpoints keeps traffic fully on the Microsoft backbone without exposing public IPs or managing a Self-Hosted IR VM.",
        "learning_guidance": "Study ADF Managed Virtual Network, Managed Private Endpoints, and the difference vs Self-Hosted IR for private connectivity."
    },
    {
        "category": "Data Engineering", "subcategory": "CI/CD & DevOps (DAB, Git Integrated Workflows)",
        "question_text": "TEST MODE Q{n} — A team wants to promote Databricks notebooks and jobs across dev/staging/prod without manual export. What is the recommended approach?",
        "options": {"A": "Export notebooks as .dbc files and upload via UI to each environment", "B": "Use Databricks Asset Bundles (DAB) with environment-specific target configs in YAML", "C": "Sync notebooks via dbfs cp in a shell script", "D": "Use Databricks Repos with branch-per-environment and manual cherry-picks"},
        "correct_answer": "B",
        "explanation": "DAB defines resources (jobs, clusters, notebooks) as code in bundle.yaml, with per-target overrides for dev/staging/prod — enabling full GitOps promotion via CI/CD pipelines.",
        "learning_guidance": "Study Databricks Asset Bundles CLI (databricks bundle deploy), bundle.yaml schema, and target overrides for multi-env promotion."
    },
    {
        "category": "Generative AI & AI Stack", "subcategory": "Agentic AI Systems",
        "question_text": "TEST MODE Q{n} — An AI agent loop keeps calling tools in circles and never produces a final answer. Which design pattern prevents this?",
        "options": {"A": "Increase the max_tokens budget so the model can reason longer", "B": "Add a step counter and force-terminate after N steps", "C": "Implement a ReAct-style Thought→Action→Observation loop with an explicit 'FINAL ANSWER' stop condition checked after each observation", "D": "Use a lower temperature to reduce hallucinated tool calls"},
        "correct_answer": "C",
        "explanation": "The ReAct pattern with an explicit terminal state check gives the agent a structured exit path. Pure step limits kill productive long chains; temperature doesn't fix logic loops.",
        "learning_guidance": "Study ReAct prompting pattern, LangGraph conditional edges for terminal state, and tool-call loop detection strategies."
    },
    {
        "category": "Core Data Platform", "subcategory": "Snowflake",
        "question_text": "TEST MODE Q{n} — A Snowflake table is queried by 50 concurrent BI users causing warehouse queuing. What is the most appropriate scaling strategy?",
        "options": {"A": "Resize the warehouse to X-Large to increase compute", "B": "Enable Multi-cluster Warehouse with auto-scale min=1 max=5", "C": "Create 50 separate warehouses, one per user", "D": "Move the table to a transient database to reduce overhead"},
        "correct_answer": "B",
        "explanation": "Multi-cluster Warehouse auto-scales additional clusters to handle concurrency queuing — the exact scenario it's designed for. Resizing only increases per-query parallelism, not concurrency.",
        "learning_guidance": "Study Snowflake Multi-cluster Warehouse auto-scale vs maximized mode, concurrency vs performance scaling, and credit consumption."
    },
    {
        "category": "Data Architecture", "subcategory": "Real-Time vs Batch Architecture",
        "question_text": "TEST MODE Q{n} — A startup wants sub-second personalization for an e-commerce site. Their data team is small (3 engineers). Which architecture is most pragmatic?",
        "options": {"A": "Full Lambda architecture with Kafka, Flink, and a separate batch layer", "B": "Kappa architecture: Kafka + Flink for all processing, single code path", "C": "Databricks Structured Streaming on Delta Lake with a low-latency serving layer (Redis)", "D": "Nightly batch jobs with a CDN cache refresh"},
        "correct_answer": "C",
        "explanation": "Structured Streaming on Delta + Redis combines manageable operational overhead (no Flink cluster) with sub-second read latency. Kappa and Lambda are operationally heavy for a 3-person team.",
        "learning_guidance": "Study Databricks Structured Streaming triggers (processingTime, availableNow), Delta table streaming reads, and Redis as a feature store."
    },
    {
        "category": "Claude & Anthropic Stack", "subcategory": "Claude Tool Use & Agentic Workflows",
        "question_text": "TEST MODE Q{n} — You are building a multi-step research agent using Claude. The agent must search, summarise, then write a report. Which orchestration approach gives the best reliability?",
        "options": {"A": "Single prompt asking Claude to search, summarise, and write all at once", "B": "Chain of three separate Claude calls with outputs passed as inputs, using tool_use for search", "C": "Ask Claude to generate Python code that performs all three steps and execute it", "D": "Use Claude with a system prompt listing all three steps and rely on it to self-sequence"},
        "correct_answer": "B",
        "explanation": "Explicit chaining with tool_use for the search step gives deterministic sequencing, observable intermediate outputs, and retry-ability per step — critical for production agent reliability.",
        "learning_guidance": "Study Anthropic multi-turn tool_use patterns, result passing between turns, and the orchestrator-worker agent pattern."
    },
    {
        "category": "Data Engineering", "subcategory": "Observability & Pipeline Reliability",
        "question_text": "TEST MODE Q{n} — A critical daily pipeline silently produces empty Delta tables due to an upstream schema change. How do you detect this proactively?",
        "options": {"A": "Check the pipeline logs manually each morning", "B": "Add a Great Expectations / DLT expectation on row_count > 0 and alert on failure", "C": "Add a try/except block that emails on exception", "D": "Query the Delta table with COUNT(*) in a downstream job and fail loudly"},
        "correct_answer": "B",
        "explanation": "Data quality expectations (Great Expectations or DLT quarantine rules) enforce contracts at ingestion time, catching schema drift and empty loads before they propagate downstream.",
        "learning_guidance": "Study Delta Live Tables expectations (EXPECT, EXPECT OR DROP, EXPECT OR FAIL), Great Expectations checkpoints, and pipeline observability patterns."
    },
    {
        "category": "Generative AI & AI Stack", "subcategory": "Vector Stores & Embeddings",
        "question_text": "TEST MODE Q{n} — Semantic search on a 10M document corpus is returning stale results after daily document updates. What is the most scalable indexing strategy?",
        "options": {"A": "Rebuild the entire vector index nightly", "B": "Use an HNSW index with incremental upsert on changed document IDs only", "C": "Delete and re-insert all vectors on each update cycle", "D": "Increase the embedding dimension to improve freshness accuracy"},
        "correct_answer": "B",
        "explanation": "HNSW with upsert-by-ID handles incremental updates efficiently — only changed documents are re-embedded and merged, avoiding full index rebuilds for a 10M corpus.",
        "learning_guidance": "Study HNSW vs IVF index trade-offs, Pinecone/Weaviate/pgvector upsert semantics, and delta-based re-indexing pipelines."
    },
    {
        "category": "Cloud Platforms", "subcategory": "Multi-Cloud Strategy",
        "question_text": "TEST MODE Q{n} — An enterprise has ML workloads on GCP Vertex AI and analytics on Azure Synapse. They want a unified governance layer. What is the recommended approach?",
        "options": {"A": "Replicate all data to a single cloud and deprecate the other", "B": "Use Microsoft Purview as a multi-cloud data catalog with scanning connectors for GCP", "C": "Build a custom metadata API that aggregates both catalogs", "D": "Enforce governance at the application layer only"},
        "correct_answer": "B",
        "explanation": "Microsoft Purview provides native Azure integration plus GCP/AWS scanning connectors, giving unified lineage, classification, and policy across clouds without data movement.",
        "learning_guidance": "Study Microsoft Purview multi-cloud scanning, data map, sensitivity labels, and integration with Unity Catalog for Databricks lineage."
    },
    {
        "category": "Core Data Platform", "subcategory": "Azure Databricks",
        "question_text": "TEST MODE Q{n} — A Databricks job fails intermittently with 'RESOURCE_DOES_NOT_EXIST' on Delta table reads during peak hours. What is the most likely cause and fix?",
        "options": {"A": "The table was dropped; restore from Delta time travel", "B": "Concurrent VACUUM operations are removing files referenced by in-flight queries; set retentionDurationCheck to 30 days", "C": "The cluster is auto-terminating mid-job; increase auto-termination timeout", "D": "Delta transaction log is corrupt; run FSCK REPAIR TABLE"},
        "correct_answer": "B",
        "explanation": "VACUUM with a short retention window can delete files still referenced by concurrent readers. Setting a safe retention window (>=7 days, >=30 for active workloads) prevents this race condition.",
        "learning_guidance": "Study Delta VACUUM retention settings, spark.databricks.delta.retentionDurationCheck.enabled, and concurrent read/write isolation levels."
    },
    {
        "category": "Data Architecture", "subcategory": "Data Governance & Cataloguing",
        "question_text": "TEST MODE Q{n} — A regulated financial firm needs full column-level lineage from raw ingestion to BI dashboards across Databricks and Power BI. What combination provides this?",
        "options": {"A": "Manual documentation in Confluence updated by engineers", "B": "Unity Catalog system tables (system.access.column_lineage) + Microsoft Purview Power BI lineage connector", "C": "dbt docs generate pushed to a static S3 site", "D": "Azure Monitor logs parsed for table-level access"},
        "correct_answer": "B",
        "explanation": "Unity Catalog system tables capture column-level lineage natively within Databricks. Purview's Power BI connector extends that lineage to the BI layer — covering the full regulated data chain.",
        "learning_guidance": "Study Unity Catalog system.access tables, column_lineage schema, and Microsoft Purview Power BI scanner configuration."
    },
    {
        "category": "Generative AI & AI Stack", "subcategory": "MLflow for Model Registry & Experiments",
        "question_text": "TEST MODE Q{n} — A data science team wants to promote a challenger model to production only if it outperforms the champion on a held-out validation set. How do you implement this gate?",
        "options": {"A": "Manually compare metrics in a notebook and update the serving endpoint", "B": "Use MLflow Model Registry transition with a validation job: compare challenger vs champion metrics, programmatically set stage to 'Production' only if challenger wins", "C": "A/B test in production and roll back if error rate increases", "D": "Always promote the newest model version automatically"},
        "correct_answer": "B",
        "explanation": "MLflow Registry lifecycle (Staging→Production transition) with a programmatic validation job enforces the champion/challenger gate reproducibly — aligned with MLOps best practices.",
        "learning_guidance": "Study MLflow MlflowClient.transition_model_version_stage, model aliases (MLflow 2.x), and champion/challenger evaluation patterns."
    },
    {
        "category": "Claude & Anthropic Stack", "subcategory": "Cost Optimisation with Prompt Caching",
        "question_text": "TEST MODE Q{n} — You have a RAG system where every user query appends retrieved chunks (avg 4000 tokens) before a 500-token instruction block. Claude API costs are high. What is the optimal caching strategy?",
        "options": {"A": "Cache the retrieved chunks as they are the largest token block", "B": "Place the static system/instruction block first with cache_control: ephemeral so it's cached across requests", "C": "Reduce chunk size to 1000 tokens to lower cost", "D": "Switch to Claude Haiku for all RAG queries to reduce per-token cost"},
        "correct_answer": "B",
        "explanation": "Prompt caching works on static prefixes. Placing the stable instruction block first with cache_control lets Anthropic cache it, reducing input costs by ~90% for the cached portion across all requests.",
        "learning_guidance": "Study Anthropic prompt caching docs: cache_control placement, minimum cacheable token thresholds (1024 for Sonnet), and cache TTL (5 minutes)."
    },
]


@router.get("/sessions/{session_id}/questions")
async def get_questions(session_id: str):
    if session_id == "11111111-1111-1111-1111-111111111111":
        total = bypass_session.get("total_questions") or \
                settings.config.get("session_config", {}).get("questions_per_session", 20)

        # Filter templates to only the categories the user selected
        selected_cats = set(bypass_session.get("categories", {}).keys())
        if selected_cats:
            pool = [t for t in _BYPASS_QUESTION_TEMPLATES if t["category"] in selected_cats]
            if not pool:
                pool = _BYPASS_QUESTION_TEMPLATES  # fallback if nothing matches
        else:
            pool = _BYPASS_QUESTION_TEMPLATES

        questions = []
        for i in range(total):
            tmpl = pool[i % len(pool)]
            questions.append({
                "id": f"q{i + 1}",
                "question_number": i + 1,
                "category": tmpl["category"],
                "subcategory": tmpl["subcategory"],
                "question_text": tmpl["question_text"].replace("{n}", str(i + 1)),
                "options": tmpl["options"],
                "correct_answer": tmpl["correct_answer"],
                "explanation": tmpl["explanation"],
                "learning_guidance": tmpl["learning_guidance"],
            })
        return questions

    response = tbl("questions").select("*").eq("session_id", session_id).order("question_number").execute()
    return response.data


# ── Submit Answer ──────────────────────────────────────────────────────────────

class AnswerSubmit(BaseModel):
    question_id: str
    user_answer: str
    time_taken_seconds: int


@router.post("/sessions/{session_id}/answers")
async def submit_answer(session_id: str, answer: AnswerSubmit):
    if session_id == "11111111-1111-1111-1111-111111111111":
        # Use same filtered pool as get_questions so correct_answer matches what was served
        selected_cats = set(bypass_session.get("categories", {}).keys())
        pool = [t for t in _BYPASS_QUESTION_TEMPLATES if t["category"] in selected_cats] \
               if selected_cats else _BYPASS_QUESTION_TEMPLATES
        if not pool:
            pool = _BYPASS_QUESTION_TEMPLATES
        try:
            idx = int(answer.question_id.lstrip("q")) - 1
            tmpl = pool[idx % len(pool)]
        except (ValueError, IndexError):
            tmpl = pool[0]
        correct = tmpl["correct_answer"]
        is_correct = answer.user_answer.strip() == correct
        return {
            "is_correct": is_correct,
            "correct_answer": correct,
            "explanation": tmpl["explanation"],
            "learning_guidance": tmpl["learning_guidance"] if not is_correct else None
        }

    q_resp = tbl("questions").select("*").eq("id", answer.question_id).execute()
    if not q_resp.data:
        raise HTTPException(status_code=404, detail="Question not found")

    question = q_resp.data[0]
    is_correct = (answer.user_answer.strip() == question["correct_answer"])

    tbl("answers").insert({
        "session_id": session_id,
        "question_id": answer.question_id,
        "user_answer": answer.user_answer,
        "is_correct": is_correct,
        "time_taken_seconds": answer.time_taken_seconds
    }).execute()

    # Update performance tracking
    user_resp = tbl("sessions").select("user_id, difficulty").eq("id", session_id).execute()
    if user_resp.data:
        u = user_resp.data[0]
        perf_resp = tbl("performance_tracking").select("*").match({
            "user_id": u["user_id"],
            "category": question["category"],
            "difficulty": u["difficulty"]
        }).execute()

        if perf_resp.data:
            perf = perf_resp.data[0]
            tbl("performance_tracking").update({
                "total_attempted": perf["total_attempted"] + 1,
                "total_correct": perf["total_correct"] + (1 if is_correct else 0)
            }).eq("id", perf["id"]).execute()
        else:
            tbl("performance_tracking").insert({
                "user_id": u["user_id"],
                "category": question["category"],
                "subcategory": question.get("subcategory"),
                "difficulty": u["difficulty"],
                "total_attempted": 1,
                "total_correct": 1 if is_correct else 0
            }).execute()

    return {
        "is_correct": is_correct,
        "correct_answer": question["correct_answer"],
        "explanation": question["explanation"],
        "learning_guidance": question["learning_guidance"] if not is_correct else None
    }


# ── Admin: Add to Question Bank ────────────────────────────────────────────────

@router.post("/admin/bank")
async def add_question_to_bank(question: dict):
    required = {"category", "subcategory", "difficulty", "question_text", "options", "correct_answer", "explanation"}
    missing = required - question.keys()
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required fields: {missing}")
    total = save_to_bank(question)
    return {"status": "added", "bank_total": total}


@router.get("/admin/bank")
async def get_bank():
    if BANK_PATH.exists():
        with open(BANK_PATH, "r", encoding="utf-8") as f:
            bank = json.load(f)
        return {"total": len(bank), "questions": bank}
    return {"total": 0, "questions": []}
