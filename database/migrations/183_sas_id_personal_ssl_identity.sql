-- SSL identity fields on the existing SAS sailor table.
-- Nullable only. Does not create sailors. Idempotent (IF NOT EXISTS).
-- Apply: psql "$DB_URL" -f database/migrations/183_sas_id_personal_ssl_identity.sql

ALTER TABLE public.sas_id_personal
  ADD COLUMN IF NOT EXISTS ssl_id BIGINT,
  ADD COLUMN IF NOT EXISTS ssl_slug TEXT,
  ADD COLUMN IF NOT EXISTS ssl_profile_url TEXT,
  ADD COLUMN IF NOT EXISTS ssl_match_status TEXT,
  ADD COLUMN IF NOT EXISTS ssl_last_checked_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sas_id_personal_ssl_id
  ON public.sas_id_personal (ssl_id)
  WHERE ssl_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_sas_id_personal_ssl_slug
  ON public.sas_id_personal (ssl_slug)
  WHERE ssl_slug IS NOT NULL;
