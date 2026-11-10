-- Real human site traffic (not login sessions). Used by /api/traffic/* and /admin/api/analytics-traffic.
-- Safe to re-run.

CREATE TABLE IF NOT EXISTS public.site_traffic_events (
  id              bigserial PRIMARY KEY,
  visitor_id      text NOT NULL,
  visit_id        text NOT NULL,
  event_type      text NOT NULL,
  path            text,
  referrer        text,
  source_channel  text,
  utm_source      text,
  utm_medium      text,
  utm_campaign    text,
  scroll_pct      integer,
  click_text      text,
  click_href      text,
  click_selector  text,
  duration_ms     integer,
  page_visible_ms integer,
  is_bot          boolean NOT NULL DEFAULT false,
  ip_address      text,
  user_agent      text,
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_site_traffic_created
  ON public.site_traffic_events (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_site_traffic_visit
  ON public.site_traffic_events (visit_id, created_at);

CREATE INDEX IF NOT EXISTS idx_site_traffic_human_type_created
  ON public.site_traffic_events (created_at DESC)
  WHERE is_bot = false;

CREATE INDEX IF NOT EXISTS idx_site_traffic_source_created
  ON public.site_traffic_events (source_channel, created_at DESC)
  WHERE is_bot = false AND event_type = 'visit_start';
