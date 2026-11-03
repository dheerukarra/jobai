CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    canonical_name TEXT NOT NULL UNIQUE,
    website TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url TEXT NOT NULL,
    canonical_key TEXT NOT NULL UNIQUE,
    fingerprint TEXT NOT NULL,
    title TEXT NOT NULL,
    company_id INTEGER REFERENCES companies(id),
    location TEXT,
    remote INTEGER NOT NULL DEFAULT 0 CHECK (remote IN (0,1)),
    posted_at TEXT,
    description TEXT,
    ats TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN
        ('new','scored','shortlisted','skipped','applied','closed')),
    first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (source, external_id)
);
CREATE INDEX idx_jobs_fingerprint ON jobs(fingerprint);
CREATE INDEX idx_jobs_status ON jobs(status);

CREATE TABLE job_scores (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    reasons TEXT,
    model TEXT,
    scored_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    route TEXT NOT NULL CHECK (route IN ('auto','assisted','skip')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN
        ('pending','tailored','ready','submitted','failed','skipped')),
    resume_path TEXT,
    answers_json TEXT,
    submitted_at TEXT,
    error TEXT
);

CREATE TABLE llm_calls (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    purpose TEXT NOT NULL,
    in_tokens INTEGER NOT NULL DEFAULT 0 CHECK (in_tokens >= 0),
    cached_tokens INTEGER NOT NULL DEFAULT 0 CHECK (cached_tokens >= 0),
    out_tokens INTEGER NOT NULL DEFAULT 0 CHECK (out_tokens >= 0),
    cost_micro_usd INTEGER NOT NULL DEFAULT 0 CHECK (cost_micro_usd >= 0),
    ref TEXT
);
CREATE INDEX idx_llm_calls_ts ON llm_calls(ts);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    kind TEXT NOT NULL,
    ref TEXT,
    detail TEXT
);
