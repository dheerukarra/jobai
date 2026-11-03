-- WP1b discovery: new project file, forward-only. Callers: jobai.discovery.boards.
-- ATS board slugs harvested from posting URLs; never written to config/companies.yaml automatically.
CREATE TABLE discovered_boards (
    id INTEGER PRIMARY KEY,
    ats TEXT NOT NULL,
    slug TEXT NOT NULL COLLATE NOCASE,
    first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    source TEXT NOT NULL,
    verified_at TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','alive','dead')),
    detail TEXT,
    UNIQUE (ats, slug)
);
CREATE INDEX idx_discovered_boards_status ON discovered_boards(status);
