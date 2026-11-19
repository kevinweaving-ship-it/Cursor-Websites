-- Staging / audit support for authorised SAS DOB reconciliation.
-- DO NOT auto-apply to production from CI or agents.
-- Apply only after REA schema verification and human authorisation.
--
-- Target DB (live): sailors_master
-- Target sailor table: public.sas_id_personal
--
-- This file creates companion objects only. It does not UPDATE sas_id_personal.

BEGIN;

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.sasms_dob_source_batch (
    batch_id            bigserial PRIMARY KEY,
    loaded_at           timestamptz NOT NULL DEFAULT now(),
    source_filename     text NOT NULL,
    source_sha256       text NOT NULL,
    expected_sha256     text,
    sha_verified        boolean NOT NULL DEFAULT false,
    row_count           integer,
    notes               text
);

CREATE TABLE IF NOT EXISTS staging.sasms_dob_source_row (
    batch_id            bigint NOT NULL REFERENCES staging.sasms_dob_source_batch(batch_id),
    source_row          integer NOT NULL,
    sas_id              text NOT NULL,
    first_name          text,
    last_name           text,
    full_name           text,
    date_of_birth       date,
    year_of_birth       integer,
    membership_status   text,
    PRIMARY KEY (batch_id, source_row)
);

CREATE INDEX IF NOT EXISTS sasms_dob_source_row_sas_id_idx
    ON staging.sasms_dob_source_row (sas_id);

CREATE TABLE IF NOT EXISTS staging.sasms_dob_decision (
    decision_id         bigserial PRIMARY KEY,
    batch_id            bigint NOT NULL REFERENCES staging.sasms_dob_source_batch(batch_id),
    decided_at          timestamptz NOT NULL DEFAULT now(),
    source_row          integer,
    sas_id              text NOT NULL,
    action              text NOT NULL,  -- apply|flag|ignore|skip|noop
    reason              text NOT NULL,
    flags               text[] NOT NULL DEFAULT '{}',
    set_date_of_birth   date,
    set_year_of_birth   integer,
    preserve_date_of_birth date,
    preserve_year_of_birth integer,
    details             jsonb NOT NULL DEFAULT '{}'::jsonb,
    applied_at          timestamptz
);

CREATE INDEX IF NOT EXISTS sasms_dob_decision_sas_id_idx
    ON staging.sasms_dob_decision (sas_id);

CREATE INDEX IF NOT EXISTS sasms_dob_decision_action_idx
    ON staging.sasms_dob_decision (action);

-- Read-only validation helpers (run after loading a batch; no writes to sas_id_personal).

-- Rows whose legacy status is Lapsed (must be ignored by importer):
-- SELECT * FROM staging.sasms_dob_source_row
-- WHERE lower(trim(membership_status)) = 'lapsed';

-- Exact SAS ID + name verification preview:
-- SELECT s.sas_id, s.full_name AS src_name, p.full_name AS db_name,
--        p.date_of_birth, p.year_of_birth
-- FROM staging.sasms_dob_source_row s
-- LEFT JOIN public.sas_id_personal p ON p.sa_sailing_id::text = s.sas_id
-- WHERE s.batch_id = :batch_id;

-- DOB protection check: decisions that would touch an existing DOB must be flags only:
-- SELECT * FROM staging.sasms_dob_decision
-- WHERE preserve_date_of_birth IS NOT NULL AND action = 'apply';

COMMIT;
