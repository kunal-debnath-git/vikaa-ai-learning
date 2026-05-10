# Vikaa.AI — Leadership Interview Prep System

> A personal AI-powered interview simulator for Lead, Principal, and CTO-level roles  
> in Data, Cloud, and GenAI at Fortune 100 companies.

---

## Purpose

Built for professionals preparing for senior leadership technical interviews — the kind where you are expected to design systems, justify architectural trade-offs, and demonstrate executive-level thinking. Every question is scenario-based (no trivia, no syntax questions).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.11+ |
| Database | Supabase (PostgreSQL) — schema: `vikaa_exam_assist` |
| AI — Gemini | Google Gemini 2.0 Flash (`gemini-2.0-flash`) |
| AI — Claude | Anthropic Claude Sonnet 4.6 (`claude-sonnet-4-6`) |
| Frontend | Single-page app — Alpine.js + Tailwind CSS (CDN) |
| Server | Uvicorn (ASGI) on port 9000 |
| Auth | Email-based identity — no OAuth, no passwords |

---

## Project Structure

```
e:\_VIKAA-AI-Learning\
│
├── main.py                    # FastAPI app entry point, router registration, static file serving
├── start.bat                  # One-click launcher — creates venv, installs deps, opens browser
├── requirements.txt           # Python dependencies
├── runtime.txt                # Python version pin (for deployment)
├── render.yaml                # Render.com deployment config
├── .env                       # Secret keys (Supabase, Gemini, Anthropic) — never commit
│
├── backend\
│   ├── config.py              # Pydantic settings loader — reads .env and config.json
│   ├── config.json            # Roles, categories, LLM providers, difficulty levels, session config
│   ├── db.py                  # Supabase client, schema-scoped tbl() helper, bypass_session store
│   ├── llm.py                 # Gemini and Claude async call wrappers
│   ├── question_gen.py        # Core question generation engine (all 3 brain modes)
│   ├── question_bank.json     # Local static question bank (used in Bank mode)
│   ├── schema.sql             # Supabase table definitions — run once to set up DB
│   └── routers\
│       ├── users.py           # POST /api/users — create or fetch user by email
│       ├── sessions.py        # POST /api/sessions — create session, PATCH complete
│       ├── questions.py       # GET/POST questions, submit answers, admin bank endpoints
│       └── analytics.py      # GET performance, sessions history, GET /api/config
│
└── frontend\
    └── index.html             # Complete single-page app (Alpine.js + Tailwind)
```

---

## Running Locally

### One-click (recommended)

Double-click **`start.bat`** from anywhere (desktop shortcut works).

It will:
1. Change directory to `e:\_VIKAA-AI-Learning` (hardcoded — safe to run from desktop)
2. Check Python is installed
3. Create `venv` in the project folder if it does not exist
4. Run `pip install -r requirements.txt` (fast no-op if already installed)
5. Check `.env` exists (warns but continues if missing)
6. Open `http://localhost:9000` in the browser after 3 seconds
7. Start uvicorn on port 9000

Press **Ctrl+C** in the terminal to stop.

### Manual

```powershell
cd e:\_VIKAA-AI-Learning
.\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 9000
```

Then open: **http://localhost:9000**

> **Important:** Always access the app through the FastAPI server (`localhost:9000`).  
> Opening `index.html` directly in VS Code Live Server (port 5500) will break all API calls.

---

## Environment Setup (.env)

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key

# LLM Providers
GEMINI_API_KEY=AIza...
GOOGLE_API_KEY=AIza...         # same as GEMINI_API_KEY
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Supabase Setup

1. Go to [supabase.com](https://supabase.com) → create a new project
2. Open **SQL Editor** → paste the full contents of `backend\schema.sql` → Run
3. Copy **Project URL** and **anon key** into `.env`

Schema is created under a dedicated PostgreSQL schema: `vikaa_exam_assist`

---

## Database Schema

| Table | Purpose |
|---|---|
| `users` | Stores name + email (UUID primary key, no passwords) |
| `sessions` | Each exam session — role, difficulty, LLM, categories, score |
| `questions` | All generated questions stored per session (20 per session) |
| `answers` | User's submitted answers with correctness and time taken |
| `performance_tracking` | Aggregated accuracy per user, per category, per difficulty |

All tables live under the `vikaa_exam_assist` schema. The `tbl()` helper in `db.py` scopes every query to this schema automatically.

---

## Target Roles

### Lead Data Solution Architect (`architect`)

System design, enterprise architecture, governance, platform selection, migration planning, cost optimisation, solution proposals.

### Lead Data Engineer (`engineer`)

Scalability, production-grade pipelines, Spark optimisation, CI/CD for data, observability, API services.

### Lead AI Engineer (`ai_engineer`)

GenAI systems, RAG architectures, MLOps, model serving, Anthropic/Claude stack, AI API design.

### Chief Data Architect / CTO (`cto`)

Full-spectrum — enterprise strategy, build vs buy, vendor selection, security posture, team structure, board-level decision framing. Questions span multiple domains simultaneously.

---

## Topic Categories & Subcategories

### Cloud Platforms

Azure (General), Multi-Cloud Strategy, Hybrid Architecture, Azure Networking & Security, VNet Injection & Private Link, Secrets Management (Azure Key Vault)

### Core Data Platform

Azure Data Factory (ADF), Azure Data Lake Storage Gen2 (ADLS), Azure Synapse Analytics, Azure Event Hub, Azure SQL Database, Azure Key Vault, Azure Databricks, Snowflake, Delta Lake, Unity Catalog

### Data Architecture

Medallion Architecture (Bronze/Silver/Gold), Lakehouse vs Data Warehouse, Lakehouse Architecture — When & Where to Apply, Data Warehouse Architecture — When & Where to Apply, Databricks vs Snowflake Architecture Trade-offs, Data Vault 2.0, Star Schema & Dimensional Modelling, Real-Time vs Batch Architecture, Data Governance & Cataloguing, FinOps & Cost Optimization, Cluster Optimization Strategies

### Data Engineering

PySpark & Spark Optimization (Data Skew, Shuffle Tuning), Delta Live Tables (DLT), Auto Loader & Streaming, Snowpipe & Streams (CDC), Metadata-Driven Pipelines, CI/CD & DevOps (DAB, Git Integrated Workflows), Observability & Pipeline Reliability, Z-Ordering & Liquid Clustering, Photon Engine Performance

### Platform & Data Migration *(new)*

Core Data Migration Strategy & Patterns, On-Premises to Azure Migration (Lift-Shift vs Re-architect), Database Platform Migration (SQL Server / Oracle to Azure SQL / Synapse), Data Warehouse Migration to Cloud (Teradata / Netezza to Azure), Application & Workload Migration to Azure, High-Volume & Large-Scale Data Migration (PB-scale), Migration Risk / Cutover Planning / Rollback Strategy, Azure Migrate & Database Migration Service Tooling

### API Design & System Integration *(new)*

REST API Design Principles for Data Platforms, FastAPI for Data & AI Services, API Gateway Patterns (Azure API Management), Event-Driven Integration Architecture, Real-Time Data API & Streaming Integration, GraphQL vs REST for Data Products, API Security (OAuth 2.0, API Keys, Rate Limiting), Microservices Integration Patterns for Data

### Solution Architecture & Pre-Sales *(new)*

Solution Proposal & Architecture Framing, Business Case Development & TCO Analysis, Platform Evaluation & Vendor Selection, Architecture Decision Records (ADRs), RFP Response & Proof-of-Concept Design, Executive & Stakeholder Communication, Scope Definition & Risk Identification in Proposals, Estimation & Delivery Roadmap Planning

### Security, Compliance & Governance *(new)*

Data Security Architecture for Cloud Platforms, Regulatory Compliance (GDPR / CCPA / SOX / HIPAA) in Data Platforms, PII Masking / Tokenisation & Data Anonymisation, Zero Trust Architecture for Data & AI Platforms, Identity & Access Management (IAM, RBAC, ABAC), Encryption at Rest & In Transit, Data Lineage / Audit Trails & Compliance Reporting, Insider Threat & Data Exfiltration Prevention

### Enterprise Architecture & CTO Strategy *(new)*

Enterprise Data Strategy & Digital Transformation, Build vs Buy Decisions at Enterprise Scale, Data Team Structure & Platform Engineering Organisation, Technology Roadmap Planning & Prioritisation, Data Product Thinking & Internal Data Marketplace, Disaster Recovery & Business Continuity for Data Platforms, Data Culture / Change Management & Adoption, M&A Data Integration & Platform Consolidation

### Generative AI & AI Stack

Generative AI (General Concepts), RAG – All Patterns (Naive, Advanced, Agentic), LangChain & Semantic Kernel, Agentic AI Systems, Vector Stores & Embeddings, LLMs: Gemini, Claude, Llama 3, MLflow for Model Registry & Experiments, Real-Time Inference Architecture, Serving & Scalability (Serverless Model Serving), Conversational AI/BI Systems

### Claude & Anthropic Stack
Claude API & Prompt Engineering, Claude Certified Architect Patterns, Multi-Model Strategy (Claude + Gemini + Llama), Claude in Enterprise RAG Pipelines, Responsible AI & Constitutional AI, Claude Tool Use & Agentic Workflows, Cost Optimisation with Prompt Caching

---

## Brain Modes

### 1. Pure LLM — Fresh AI Generation (`llm`)

Every question is generated fresh by the chosen LLM at exam time.  
Most creative and varied output. No history or bank used.  
Takes ~30 seconds to generate all 20 questions.

### 2. Adaptive — Target Your Weak Spots (`adaptive`)

Reads your past performance from the analytics dashboard.  
Focuses the LLM on categories where your accuracy is **below 70%**.  
If you are scoring well everywhere, it switches to harder consolidation questions.

### 3. Question Bank — AI-Augmented Pool (`bank`)

Up to **15%** of questions pulled from the local `question_bank.json`.  
Remaining **85%** generated fresh by the LLM.  
Useful for a consistent baseline mixed with AI variety.

> **When to use what:** Start with Pure LLM for your first sessions. Switch to Adaptive once you have performance history built up in the dashboard.

---

## Question Generation Pipeline

1. User submits exam config (role, difficulty, LLM, categories, brain mode)
2. Session created in Supabase (or in-memory for test bypass)
3. Frontend calls `POST /api/sessions/{id}/generate`
4. Backend builds a scenario-focused system prompt with current market trends injected
5. LLM called in **batches of 5 questions** to stay within token limits
6. For Adaptive mode: weak areas (<70% accuracy) are injected into the system prompt
7. For Bank mode: up to 3 questions from local bank pre-pended before LLM generation
8. Spaced repetition: questions answered incorrectly in the last 3 sessions are automatically re-queued
9. All 20 questions stored in Supabase and returned to the frontend

---

## Market Intelligence (Injected into Every Prompt)

The LLM system prompt is enriched with current Fortune 100 hiring trends (configured in `config.json`):

- Agentic RAG patterns
- Unity Catalog migration from traditional Hive Metastore
- Snowflake vs Databricks cost-benefit analysis at scale
- FinOps for multi-cloud data estates
- Transition from Data Mesh to centralized governance with decentralized ownership

---

## LLM Providers

| Provider | Model | Max Tokens |
|---|---|---|
| Gemini (default) | `gemini-2.0-flash` | 8000 |
| Claude | `claude-sonnet-4-6` | 8000 |

Gemini SDK is synchronous — calls are wrapped in `asyncio.to_thread()` to avoid blocking the event loop.  
Claude uses the official `anthropic.AsyncAnthropic` client.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check — returns version |
| GET | `/api/config` | Full frontend config (roles, categories, providers, trends) |
| POST | `/api/users` | Create or upsert user by email |
| GET | `/api/users/{email}` | Fetch user by email |
| POST | `/api/sessions` | Create a new exam session |
| GET | `/api/sessions/{id}` | Get session details |
| PATCH | `/api/sessions/{id}/complete` | Mark session complete with final score |
| POST | `/api/sessions/{id}/generate` | Trigger LLM question generation |
| GET | `/api/sessions/{id}/questions` | Fetch all questions for a session |
| POST | `/api/sessions/{id}/answers` | Submit an answer, get instant feedback |
| GET | `/api/users/{user_id}/performance` | Aggregated performance per category |
| GET | `/api/users/{user_id}/sessions` | Session history for a user |
| GET | `/api/admin/bank` | View all questions in the local question bank |
| POST | `/api/admin/bank` | Add a question to the local question bank |

Interactive API docs: **http://localhost:9000/docs**

---

## Test / Bypass Mode

For local testing without a real Supabase account.

| Field | Value |
|---|---|
| Email | `test@testemail.com` |
| User UUID | `00000000-0000-0000-0000-000000000000` |
| Session UUID | `11111111-1111-1111-1111-111111111111` |

**What the bypass does:**
- Skips all Supabase reads/writes
- Still calls the real LLM pipeline (so prompt changes are visible immediately)
- Falls back to 20 static template questions if no categories are selected or LLM fails
- Analytics returns empty arrays (no history to show)

The bypass is active in every router — no environment flag needed.

---

## Session Config (config.json)

```json
"session_config": {
    "questions_per_session": 20,
    "time_per_question_seconds": 120
}
```

Change `questions_per_session` to adjust exam length. `time_per_question_seconds` is tracked per answer but not enforced as a hard cutoff.

---

## Extending the System

**Add a new subcategory:**  
Edit `backend\config.json` → find the parent category → add the subcategory string to the `subcategories` array. No code change needed — the frontend reads config dynamically from `/api/config`.

**Add a question to the bank:**  
`POST /api/admin/bank` with JSON body:
```json
{
  "category": "Data Architecture",
  "subcategory": "Medallion Architecture (Bronze/Silver/Gold)",
  "difficulty": "Hard",
  "question_text": "...",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "correct_answer": "B",
  "explanation": "...",
  "learning_guidance": "..."
}
```

**Switch default LLM model:**  
Edit `backend\config.json` → `llm_providers.gemini.model` or `llm_providers.claude.model`.
