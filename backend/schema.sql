-- ============================================================
-- Advanced Interview Prep System — Supabase Schema > "vikaa_exam_assist"
-- ============================================================

create schema if not exists vikaa_exam_assist;

-- Users (simple, no auth required — identified by name/email)
CREATE TABLE IF NOT EXISTS vikaa_exam_assist.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions
CREATE TABLE IF NOT EXISTS vikaa_exam_assist.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES vikaa_exam_assist.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,               -- 'architect', 'engineer', 'ai_engineer', 'cto'
    difficulty TEXT NOT NULL,         -- 'easy', 'medium', 'hard'
    llm_provider TEXT NOT NULL,       -- 'claude', 'gemini'
    categories JSONB NOT NULL,        -- selected categories/subcategories
    total_questions INT DEFAULT 20,
    score INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);


-- Questions (generated and stored per session)
CREATE TABLE IF NOT EXISTS vikaa_exam_assist.questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES vikaa_exam_assist.sessions(id) ON DELETE CASCADE,
    question_number INT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    question_text TEXT NOT NULL,
    options JSONB NOT NULL,           -- {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer TEXT NOT NULL,     -- "A", "B", "C", or "D"
    explanation TEXT NOT NULL,        -- why correct answer is architecturally superior
    learning_guidance TEXT,           -- for wrong answers
    created_at TIMESTAMPTZ DEFAULT NOW()
);

    -- session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,

-- Answers (user responses)
CREATE TABLE IF NOT EXISTS vikaa_exam_assist.answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES vikaa_exam_assist.sessions(id) ON DELETE CASCADE,
    question_id UUID REFERENCES vikaa_exam_assist.questions(id) ON DELETE CASCADE,
    user_answer TEXT,                 -- "A", "B", "C", or "D"
    is_correct BOOLEAN,
    time_taken_seconds INT,
    answered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance tracking (aggregated per user per category)
CREATE TABLE IF NOT EXISTS vikaa_exam_assist.performance_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES vikaa_exam_assist.users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    subcategory TEXT,
    difficulty TEXT NOT NULL,
    total_attempted INT DEFAULT 0,
    total_correct INT DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, category, subcategory, difficulty)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user ON vikaa_exam_assist.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_questions_session ON vikaa_exam_assist.questions(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_session ON vikaa_exam_assist.answers(session_id);
CREATE INDEX IF NOT EXISTS idx_performance_user ON vikaa_exam_assist.performance_tracking(user_id);
