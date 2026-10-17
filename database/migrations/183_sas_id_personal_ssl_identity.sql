-- Add nullable SSL user id onto existing SAS sailor rows.
-- Does not create sailors. Does not add duplicate slug/url/status columns.
-- No DROP. Idempotent (IF NOT EXISTS).
-- Do not apply this file in this step.

ALTER TABLE public.sas_id_personal
  ADD COLUMN IF NOT EXISTS ssl_user_id BIGINT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sas_id_personal_ssl_user_id
  ON public.sas_id_personal (ssl_user_id)
  WHERE ssl_user_id IS NOT NULL;
