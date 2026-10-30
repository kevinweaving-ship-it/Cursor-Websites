# Most popular Class / Sailor / Club missing real visits

## Causes
1. **`/class/420` dropped:** `_lean_resolve_class_for_traffic` cleared digit-only
   slugs (`420` → `""`), href became `/classes`, entity row skipped.
2. **Staff excluded from popular:** signed-in Tim (165.165.*) never counted in
   Class/Sailor/Club lists despite scroll/click.
3. **UI showed only 6** entity rows while SBYC sat at ~10th.

## Fix (live)
- Keep digit-only class names (420, 470, 505)
- Include staff reals in `_lean_traffic_unified_sql` (quarantine/cloud still out)
- Entity tables show top 10
- One-shot nav engage backfill for last 24h trails

Apply: `python3 sailingsa/deploy/patch_popular_entities_420.py`
