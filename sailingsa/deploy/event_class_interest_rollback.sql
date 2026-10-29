-- =============================================================================
-- Stage 1 rollback — Event class interest
-- =============================================================================
-- Drops interest objects created by event_class_interest.sql.
-- Safe only when no production traffic depends on these tables (Stage 1 / empty).
-- DO NOT run against production unless explicitly approved as a rollback.
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.eci_reconcile_visitor_to_account(text, bigint, jsonb);
DROP FUNCTION IF EXISTS public.eci_withdraw_interest(integer, bigint, text, jsonb);
DROP FUNCTION IF EXISTS public.eci_upsert_interest(integer, text, bigint, text, integer, jsonb);

DROP VIEW IF EXISTS public.event_interest_totals;
DROP VIEW IF EXISTS public.event_class_interest_counts;

DROP TRIGGER IF EXISTS ecih_no_update ON public.event_class_interest_history;
DROP TRIGGER IF EXISTS ecih_no_delete ON public.event_class_interest_history;
DROP FUNCTION IF EXISTS public.eci_history_immutable();

DROP TABLE IF EXISTS public.event_class_interest_history;
DROP TABLE IF EXISTS public.event_class_interest;

COMMIT;
