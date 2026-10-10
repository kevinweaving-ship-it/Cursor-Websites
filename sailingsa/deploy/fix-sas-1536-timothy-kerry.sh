#!/usr/bin/env bash
# Undo the wrong table rewrite. sas_id_personal is truth.
# SAS 1536 = Tim Kerry. Stamp result helm_name from the table. Do not invent names.
# See sailingsa/deploy/SSH_LIVE.md. No api.py change. No API restart.
set -euo pipefail
SERVER=102.218.215.253
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
SSH_OPTS="-o StrictHostKeyChecking=no"
[ -f "$KEY" ] && SSH_OPTS="$SSH_OPTS -i $KEY"

ssh $SSH_OPTS "root@${SERVER}" 'psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master -v ON_ERROR_STOP=1' <<'SQL'
BEGIN;

-- Restore table row 1536 to Tim Kerry (original SAS ID table truth).
UPDATE public.sas_id_personal
SET first_name = 'Tim',
    full_name = 'Tim Kerry',
    nickname = NULL
WHERE sa_sailing_id::text = '1536'
  AND last_name = 'Kerry';

-- Stamp every 1536 result name FROM the table. Event must match us, not the other way.
UPDATE public.results r
SET helm_name = COALESCE(NULLIF(TRIM(s.full_name), ''), TRIM(s.first_name || ' ' || s.last_name))
FROM public.sas_id_personal s
WHERE s.sa_sailing_id::text = r.helm_sa_sailing_id::text
  AND r.helm_sa_sailing_id::text = '1536';

UPDATE public.results r
SET crew_name = COALESCE(NULLIF(TRIM(s.full_name), ''), TRIM(s.first_name || ' ' || s.last_name))
FROM public.sas_id_personal s
WHERE s.sa_sailing_id::text = r.crew_sa_sailing_id::text
  AND r.crew_sa_sailing_id::text = '1536';

COMMIT;

SELECT sa_sailing_id, first_name, last_name, full_name, nickname, primary_club
FROM public.sas_id_personal
WHERE sa_sailing_id::text = '1536';

SELECT r.result_id, r.helm_name, r.helm_sa_sailing_id, s.full_name,
       (r.helm_name = s.full_name) AS name_match
FROM public.results r
JOIN public.sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
WHERE r.helm_sa_sailing_id::text = '1536'
ORDER BY r.result_id;

SELECT r.result_id, r.helm_name, r.helm_sa_sailing_id, s.full_name,
       (r.helm_name = s.full_name) AS name_match
FROM public.results r
JOIN public.sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
WHERE r.result_id IN (21306,21307,21308,21309)
ORDER BY r.result_id;
SQL
