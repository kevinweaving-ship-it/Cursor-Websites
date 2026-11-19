"""Versioned roundup tables (apply later; preview builds use JSON under artifacts/)."""

DDL = """
CREATE TABLE IF NOT EXISTS roundup_event_fact (
    event_id TEXT PRIMARY KEY,
    edition_date DATE NOT NULL,
    fact_json JSONB NOT NULL,
    fact_hash TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roundup_source (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL,
    url TEXT NOT NULL,
    label TEXT NOT NULL,
    kind TEXT NOT NULL,
    fetched_at TIMESTAMPTZ,
    UNIQUE (event_id, url)
);

CREATE TABLE IF NOT EXISTS roundup_image (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    local_path TEXT,
    credit TEXT,
    score INT,
    role TEXT,
    phash TEXT
);

CREATE TABLE IF NOT EXISTS roundup_edition (
    edition_date DATE NOT NULL,
    version INT NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_line TEXT,
    PRIMARY KEY (edition_date, version)
);

CREATE TABLE IF NOT EXISTS roundup_edition_item (
    edition_date DATE NOT NULL,
    version INT NOT NULL,
    event_id TEXT NOT NULL,
    slot TEXT NOT NULL,
    story_score NUMERIC NOT NULL,
    fact_hash TEXT NOT NULL,
    PRIMARY KEY (edition_date, version, event_id)
);

CREATE TABLE IF NOT EXISTS roundup_job_log (
    id BIGSERIAL PRIMARY KEY,
    job TEXT NOT NULL,
    edition_date DATE,
    event_id TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
