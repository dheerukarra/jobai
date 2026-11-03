-- WP1a discovery: new project file, forward-only. Callers: jobai.discovery.store.
-- Adds liveness + provenance columns to jobs and an alias table for cross-source duplicates.
ALTER TABLE jobs ADD COLUMN company_slug TEXT;
ALTER TABLE jobs ADD COLUMN apply_url TEXT;
ALTER TABLE jobs ADD COLUMN last_seen_at TEXT;
ALTER TABLE jobs ADD COLUMN raw_json TEXT;
UPDATE jobs SET last_seen_at = first_seen_at WHERE last_seen_at IS NULL;
CREATE INDEX idx_jobs_last_seen ON jobs(last_seen_at);

CREATE TABLE job_aliases (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (source, external_id)
);
CREATE INDEX idx_job_aliases_job ON job_aliases(job_id);
