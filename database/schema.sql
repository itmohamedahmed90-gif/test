-- schema.sql
-- Multi-user Resume Generator schema.
-- Applied once at startup by database/connection.py::init_db()

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT NOT NULL DEFAULT 'Untitled Resume',
    -- Structured resume content, stored as a single JSON blob:
    -- { "personal": {...}, "experience": [...], "education": [...],
    --   "skills": [...], "projects": [...] }
    data_json   TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Every resume lookup is by user_id, so this index carries the whole app.
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
