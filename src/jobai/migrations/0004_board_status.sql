-- WP1c discovery: new project file, forward-only. Callers: jobai.discovery.health, runner.
-- Tracks per-board liveness so a verified-dead board (404/410/redirect) is skipped by `discover run`.
CREATE TABLE board_status (
    ats TEXT NOT NULL,
    slug TEXT NOT NULL COLLATE NOCASE,
    status TEXT NOT NULL CHECK (status IN ('ok','dead')),
    checked_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    detail TEXT,
    PRIMARY KEY (ats, slug)
);
