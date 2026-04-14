# ArchIQ — Advanced Interview Preparation System

> Leadership-level interview simulator for Data, Cloud & GenAI roles.
> Designed for professionals targeting Principal, Director, and Head of Data/AI positions at Fortune 100 companies.

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
cd interview-prep
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and fill in your keys:
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-service-role-key
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=AI...
```

### 3. Set Up Supabase
1. Go to https://supabase.com → New Project
2. Open **SQL Editor** → paste contents of `schema.sql` → Run
3. Copy your **Project URL** and **anon/service key** into `.env`

### 4. Run the App
```bash
uvicorn main:app --reload --port 8000
```

Open: **http://localhost:8000**

---

## 📁 Project Structure

```
interview-prep/
├── main.py                  # FastAPI entry point
├── config.json              # Roles, categories, LLM config
├── schema.sql               # Supabase table definitions
├── requirements.txt
├── .env.example             # Environment template
├── backend/
│   ├── config.py            # Settings loader
│   ├── database.py          # Supabase client + helpers
│   ├── llm.py               # Claude + Gemini handlers
│   ├── models.py            # Pydantic request/response models
│   ├── question_gen.py      # Question generation engine
│   └── routers/
│       ├── users.py         # User registration/lookup
│       ├── sessions.py      # Session creation + status polling
│       ├── questions.py     # Question fetch + answer submission
│       └── analytics.py     # Performance tracking + review
└── frontend/
    └── index.html           # Single-page application
```

---

## ⚙️ Configuration

Edit `config.json` to:
- Add/remove **technology sub-categories** (e.g. add "Microsoft Fabric" under Core Data Platform)
- Change **questions per session** (default: 20)
- Switch default **LLM models**

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/users/` | Create or fetch user by email |
| POST | `/api/sessions/` | Start a new exam session |
| GET | `/api/sessions/{id}/status` | Poll question generation status |
| POST | `/api/sessions/{id}/complete` | Mark session complete |
| GET | `/api/questions/session/{id}` | Get all questions for session |
| POST | `/api/questions/answer` | Submit answer + get feedback |
| GET | `/api/analytics/user/{id}` | Full user performance analytics |
| GET | `/api/analytics/session/{id}/review` | Session review with all answers |
| GET | `/api/analytics/config` | Frontend configuration |

Interactive docs: **http://localhost:8000/docs**

---

## 🧠 How Questions Are Generated

1. Session is created in Supabase
2. Background task calls LLM (Claude or Gemini) in **batches of 5**
3. Each batch uses a scenario-focused prompt — no syntax, no "what is X" questions
4. Questions are stored in Supabase as they arrive
5. Frontend polls `/status` every 2 seconds until all 20 are ready
6. Answers are submitted individually; feedback is instant

---

## 📊 Extending Categories

In `config.json`, add subcategories under any category:

```json
"Core Data Platform": {
  "subcategories": [
    "Azure Data Factory (ADF)",
    "Microsoft Fabric",       ← add here
    "Azure Databricks",
    ...
  ]
}
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11+ |
| Database | Supabase (PostgreSQL) |
| AI Engine | Anthropic Claude Sonnet / Google Gemini 1.5 Pro |
| Frontend | Vanilla HTML/CSS/JS (zero dependencies) |
| Auth | Email-based identity (no OAuth required) |
