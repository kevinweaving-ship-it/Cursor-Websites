-- Proposed, independently reviewed indexes for the exact sailor-slug predicate.
-- Audit evidence: EXPLAIN ANALYZE on 2026-11-08 scanned 26,477 rows
-- and took 335ms for a three-row surname lookup.
--
-- Requires a separately verified schema migration; DO NOT execute from CI
-- or from a read-only REA audit tool. Run each CONCURRENTLY statement outside
-- a transaction after checking free disk space, locks and existing indexes.
-- Assess a representative set of slugs using EXPLAIN ANALYZE before/after.

CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_sas_personal_slug_last_norm
ON public.sas_id_personal
  ((REPLACE(REPLACE(LOWER(TRIM(COALESCE(last_name, ''))), CHR(39), ''), '’', '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_sas_personal_slug_full_norm_trgm
ON public.sas_id_personal USING gin
  ((REPLACE(REPLACE(LOWER(TRIM(COALESCE(full_name, ''))), CHR(39), ''), '’', '')) gin_trgm_ops);

-- Do not drop any existing indexes without reviewing real query plans.
