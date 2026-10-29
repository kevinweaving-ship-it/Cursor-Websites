-- =============================================================================
-- Stage 1 — Event class interest (APPROVAL REQUIRED before production apply)
-- =============================================================================
-- Purpose: store one current interest per identity per event + immutable history.
-- Counts are derived from status='active' rows only (never cached counters).
--
-- Identities:
--   Registered sailor  → account_id (user_accounts.account_id)
--   Public visitor     → visitor_id = cookie-only ssa_vid (32-char hex); NEVER IP
--
-- Class selection:
--   class_identifier must exist on public.event_edition_classes for that event_id
--   (composite FK). class_id is optional canonical map into public.classes.
--
-- DO NOT run against production until Stage 1 is explicitly approved.
-- Apply (when approved later):
--   psql "$DB_URL" -v ON_ERROR_STOP=1 -f sailingsa/deploy/event_class_interest.sql
-- Rollback:
--   psql "$DB_URL" -v ON_ERROR_STOP=1 -f sailingsa/deploy/event_class_interest_rollback.sql
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Current interest: exactly one row per identity per event (active OR withdrawn)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.event_class_interest (
    interest_id      bigserial PRIMARY KEY,
    event_id         integer NOT NULL REFERENCES public.events(event_id),
    class_id         integer REFERENCES public.classes(class_id),
    class_identifier text NOT NULL,
    account_id       bigint REFERENCES public.user_accounts(account_id),
    visitor_id       text,
    status           text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT eci_status_chk CHECK (status IN ('active', 'withdrawn')),
    CONSTRAINT eci_one_identity_chk CHECK (
        (account_id IS NOT NULL AND visitor_id IS NULL)
        OR (account_id IS NULL AND visitor_id IS NOT NULL)
    ),
    -- Cookie-only ssa_vid shape (uuid.hex). Reject IP / free-form strings.
    CONSTRAINT eci_visitor_id_chk CHECK (
        visitor_id IS NULL OR visitor_id ~ '^[0-9a-f]{32}$'
    ),
    CONSTRAINT eci_class_identifier_chk CHECK (
        char_length(btrim(class_identifier)) BETWEEN 1 AND 80
    ),
    -- Selected class must be a verified edition class for this event.
    CONSTRAINT eci_event_class_fkey
        FOREIGN KEY (event_id, class_identifier)
        REFERENCES public.event_edition_classes (event_id, class_identifier)
);

-- One current row per registered sailor per event (incl. withdrawn).
CREATE UNIQUE INDEX IF NOT EXISTS eci_account_event_uid
    ON public.event_class_interest (event_id, account_id)
    WHERE account_id IS NOT NULL;

-- One current row per anonymous visitor per event (incl. withdrawn).
CREATE UNIQUE INDEX IF NOT EXISTS eci_visitor_event_uid
    ON public.event_class_interest (event_id, visitor_id)
    WHERE visitor_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS eci_event_active_idx
    ON public.event_class_interest (event_id)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS eci_event_class_active_idx
    ON public.event_class_interest (event_id, class_identifier)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS eci_account_idx
    ON public.event_class_interest (account_id)
    WHERE account_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS eci_visitor_idx
    ON public.event_class_interest (visitor_id)
    WHERE visitor_id IS NOT NULL;

COMMENT ON TABLE public.event_class_interest IS
    'Current event interest (active|withdrawn). One row per identity/event. Counts = status=active only.';

-- ---------------------------------------------------------------------------
-- Immutable history
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.event_class_interest_history (
    history_id       bigserial PRIMARY KEY,
    interest_id      bigint REFERENCES public.event_class_interest(interest_id),
    event_id         integer NOT NULL,
    class_id         integer,
    class_identifier text,
    account_id       bigint,
    visitor_id       text,
    action           text NOT NULL,
    from_class_id    integer,
    to_class_id      integer,
    from_class_identifier text,
    to_class_identifier   text,
    meta             jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ecih_action_chk CHECK (action IN (
        'created',
        'class_changed',
        'withdrawn',
        'reactivated',
        'reconciled_to_account'
    ))
);

CREATE INDEX IF NOT EXISTS ecih_interest_idx
    ON public.event_class_interest_history (interest_id, created_at);

CREATE INDEX IF NOT EXISTS ecih_event_idx
    ON public.event_class_interest_history (event_id, created_at);

COMMENT ON TABLE public.event_class_interest_history IS
    'Append-only interest audit. UPDATE/DELETE blocked by trigger.';

CREATE OR REPLACE FUNCTION public.eci_history_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'event_class_interest_history is immutable (% not allowed)', TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS ecih_no_update ON public.event_class_interest_history;
CREATE TRIGGER ecih_no_update
    BEFORE UPDATE ON public.event_class_interest_history
    FOR EACH ROW EXECUTE FUNCTION public.eci_history_immutable();

DROP TRIGGER IF EXISTS ecih_no_delete ON public.event_class_interest_history;
CREATE TRIGGER ecih_no_delete
    BEFORE DELETE ON public.event_class_interest_history
    FOR EACH ROW EXECUTE FUNCTION public.eci_history_immutable();

-- ---------------------------------------------------------------------------
-- Derived counts (no stored counters — total must equal sum of class counts)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.event_class_interest_counts AS
SELECT
    event_id,
    class_identifier,
    class_id,
    COUNT(*)::bigint AS interested_count
FROM public.event_class_interest
WHERE status = 'active'
GROUP BY event_id, class_identifier, class_id;

CREATE OR REPLACE VIEW public.event_interest_totals AS
SELECT
    event_id,
    COUNT(*)::bigint AS total_interested
FROM public.event_class_interest
WHERE status = 'active'
GROUP BY event_id;

-- ---------------------------------------------------------------------------
-- Transactional write helpers (Stage 2 will call these; validated in Stage 1)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.eci_upsert_interest(
    p_event_id integer,
    p_class_identifier text,
    p_account_id bigint DEFAULT NULL,
    p_visitor_id text DEFAULT NULL,
    p_class_id integer DEFAULT NULL,
    p_meta jsonb DEFAULT '{}'::jsonb
) RETURNS public.event_class_interest
LANGUAGE plpgsql
AS $$
DECLARE
    v_ident text := lower(btrim(p_class_identifier));
    v_row public.event_class_interest%ROWTYPE;
    v_prev_class_id integer;
    v_prev_class_identifier text;
    v_prev_status text;
    v_action text;
BEGIN
    IF p_event_id IS NULL THEN
        RAISE EXCEPTION 'event_id required';
    END IF;
    IF v_ident IS NULL OR v_ident = '' THEN
        RAISE EXCEPTION 'class_identifier required';
    END IF;
    IF (p_account_id IS NULL AND p_visitor_id IS NULL)
       OR (p_account_id IS NOT NULL AND p_visitor_id IS NOT NULL) THEN
        RAISE EXCEPTION 'exactly one of account_id or visitor_id required';
    END IF;
    IF p_visitor_id IS NOT NULL AND p_visitor_id !~ '^[0-9a-f]{32}$' THEN
        RAISE EXCEPTION 'visitor_id must be 32-char hex ssa_vid';
    END IF;

    -- Must be a verified edition class for this event (also enforced by FK).
    IF NOT EXISTS (
        SELECT 1 FROM public.event_edition_classes eec
        WHERE eec.event_id = p_event_id
          AND eec.class_identifier = v_ident
    ) THEN
        RAISE EXCEPTION 'class_identifier % is not configured for event %', v_ident, p_event_id;
    END IF;

    IF p_account_id IS NOT NULL THEN
        SELECT * INTO v_row
        FROM public.event_class_interest
        WHERE event_id = p_event_id AND account_id = p_account_id
        FOR UPDATE;
    ELSE
        SELECT * INTO v_row
        FROM public.event_class_interest
        WHERE event_id = p_event_id AND visitor_id = p_visitor_id
        FOR UPDATE;
    END IF;

    IF NOT FOUND THEN
        INSERT INTO public.event_class_interest (
            event_id, class_id, class_identifier, account_id, visitor_id, status
        ) VALUES (
            p_event_id, p_class_id, v_ident, p_account_id, p_visitor_id, 'active'
        )
        RETURNING * INTO v_row;

        INSERT INTO public.event_class_interest_history (
            interest_id, event_id, class_id, class_identifier,
            account_id, visitor_id, action, to_class_id, to_class_identifier, meta
        ) VALUES (
            v_row.interest_id, v_row.event_id, v_row.class_id, v_row.class_identifier,
            v_row.account_id, v_row.visitor_id, 'created',
            v_row.class_id, v_row.class_identifier, COALESCE(p_meta, '{}'::jsonb)
        );
        RETURN v_row;
    END IF;

    v_prev_class_id := v_row.class_id;
    v_prev_class_identifier := v_row.class_identifier;
    v_prev_status := v_row.status;

    IF v_prev_status = 'active'
       AND v_prev_class_identifier = v_ident
       AND v_prev_class_id IS NOT DISTINCT FROM p_class_id THEN
        -- Idempotent repeat: no double-count, no extra history noise.
        RETURN v_row;
    END IF;

    IF v_prev_status = 'withdrawn' THEN
        v_action := 'reactivated';
    ELSIF v_prev_class_identifier IS DISTINCT FROM v_ident
          OR v_prev_class_id IS DISTINCT FROM p_class_id THEN
        v_action := 'class_changed';
    ELSE
        v_action := 'reactivated';
    END IF;

    UPDATE public.event_class_interest
    SET class_id = p_class_id,
        class_identifier = v_ident,
        status = 'active',
        updated_at = now()
    WHERE interest_id = v_row.interest_id
    RETURNING * INTO v_row;

    INSERT INTO public.event_class_interest_history (
        interest_id, event_id, class_id, class_identifier,
        account_id, visitor_id, action,
        from_class_id, to_class_id,
        from_class_identifier, to_class_identifier,
        meta
    ) VALUES (
        v_row.interest_id, v_row.event_id, v_row.class_id, v_row.class_identifier,
        v_row.account_id, v_row.visitor_id, v_action,
        v_prev_class_id, v_row.class_id,
        v_prev_class_identifier, v_row.class_identifier,
        COALESCE(p_meta, '{}'::jsonb)
    );

    RETURN v_row;
END;
$$;

CREATE OR REPLACE FUNCTION public.eci_withdraw_interest(
    p_event_id integer,
    p_account_id bigint DEFAULT NULL,
    p_visitor_id text DEFAULT NULL,
    p_meta jsonb DEFAULT '{}'::jsonb
) RETURNS public.event_class_interest
LANGUAGE plpgsql
AS $$
DECLARE
    v_row public.event_class_interest%ROWTYPE;
BEGIN
    IF (p_account_id IS NULL AND p_visitor_id IS NULL)
       OR (p_account_id IS NOT NULL AND p_visitor_id IS NOT NULL) THEN
        RAISE EXCEPTION 'exactly one of account_id or visitor_id required';
    END IF;

    IF p_account_id IS NOT NULL THEN
        SELECT * INTO v_row
        FROM public.event_class_interest
        WHERE event_id = p_event_id AND account_id = p_account_id
        FOR UPDATE;
    ELSE
        SELECT * INTO v_row
        FROM public.event_class_interest
        WHERE event_id = p_event_id AND visitor_id = p_visitor_id
        FOR UPDATE;
    END IF;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'no interest row for identity/event';
    END IF;

    IF v_row.status = 'withdrawn' THEN
        RETURN v_row; -- idempotent
    END IF;

    UPDATE public.event_class_interest
    SET status = 'withdrawn', updated_at = now()
    WHERE interest_id = v_row.interest_id
    RETURNING * INTO v_row;

    INSERT INTO public.event_class_interest_history (
        interest_id, event_id, class_id, class_identifier,
        account_id, visitor_id, action,
        from_class_id, from_class_identifier, meta
    ) VALUES (
        v_row.interest_id, v_row.event_id, v_row.class_id, v_row.class_identifier,
        v_row.account_id, v_row.visitor_id, 'withdrawn',
        v_row.class_id, v_row.class_identifier, COALESCE(p_meta, '{}'::jsonb)
    );

    RETURN v_row;
END;
$$;

-- Login reconciliation: move/keep sailor interest; never double-count.
-- Sailor row wins if both were active. Visitor row becomes withdrawn.
CREATE OR REPLACE FUNCTION public.eci_reconcile_visitor_to_account(
    p_visitor_id text,
    p_account_id bigint,
    p_meta jsonb DEFAULT '{}'::jsonb
) RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_vis public.event_class_interest%ROWTYPE;
    v_acc public.event_class_interest%ROWTYPE;
    v_moved integer := 0;
BEGIN
    IF p_visitor_id IS NULL OR p_visitor_id !~ '^[0-9a-f]{32}$' THEN
        RAISE EXCEPTION 'visitor_id must be 32-char hex ssa_vid';
    END IF;
    IF p_account_id IS NULL THEN
        RAISE EXCEPTION 'account_id required';
    END IF;

    FOR v_vis IN
        SELECT * FROM public.event_class_interest
        WHERE visitor_id = p_visitor_id
        FOR UPDATE
    LOOP
        SELECT * INTO v_acc
        FROM public.event_class_interest
        WHERE event_id = v_vis.event_id AND account_id = p_account_id
        FOR UPDATE;

        IF NOT FOUND THEN
            -- Reassign visitor row to the sailor account.
            UPDATE public.event_class_interest
            SET account_id = p_account_id,
                visitor_id = NULL,
                updated_at = now()
            WHERE interest_id = v_vis.interest_id
            RETURNING * INTO v_vis;

            INSERT INTO public.event_class_interest_history (
                interest_id, event_id, class_id, class_identifier,
                account_id, visitor_id, action, to_class_id, to_class_identifier, meta
            ) VALUES (
                v_vis.interest_id, v_vis.event_id, v_vis.class_id, v_vis.class_identifier,
                p_account_id, p_visitor_id, 'reconciled_to_account',
                v_vis.class_id, v_vis.class_identifier,
                COALESCE(p_meta, '{}'::jsonb) || jsonb_build_object(
                    'previous_visitor_id', p_visitor_id,
                    'mode', 'reassigned'
                )
            );
            v_moved := v_moved + 1;
        ELSE
            -- Sailor already has a current row for this event → keep sailor, withdraw visitor.
            IF v_vis.status = 'active' THEN
                UPDATE public.event_class_interest
                SET status = 'withdrawn', updated_at = now()
                WHERE interest_id = v_vis.interest_id
                RETURNING * INTO v_vis;

                INSERT INTO public.event_class_interest_history (
                    interest_id, event_id, class_id, class_identifier,
                    account_id, visitor_id, action,
                    from_class_id, from_class_identifier, meta
                ) VALUES (
                    v_vis.interest_id, v_vis.event_id, v_vis.class_id, v_vis.class_identifier,
                    NULL, p_visitor_id, 'reconciled_to_account',
                    v_vis.class_id, v_vis.class_identifier,
                    COALESCE(p_meta, '{}'::jsonb) || jsonb_build_object(
                        'kept_account_interest_id', v_acc.interest_id,
                        'mode', 'visitor_withdrawn_account_kept'
                    )
                );
            END IF;
            v_moved := v_moved + 1;
        END IF;
    END LOOP;

    RETURN v_moved;
END;
$$;

COMMIT;
