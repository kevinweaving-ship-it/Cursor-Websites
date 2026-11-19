-- GoWiFi Openserve UPP mirror. No secrets in this file.
-- Live copy lives on box.gowifi.co.za at /root/gowifi-upp/upp.db

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    ok INTEGER NOT NULL DEFAULT 0,
    initiating_user TEXT,
    box_account TEXT,
    orders_upserted INTEGER DEFAULT 0,
    services_upserted INTEGER DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS organisations (
    id INTEGER PRIMARY KEY,
    oms_name TEXT,
    oms_code TEXT,
    cbs_name TEXT,
    cbs_id TEXT,
    clarify_ban TEXT,
    customer_code TEXT,
    status TEXT,
    isp_volume INTEGER,
    email_address TEXT,
    bundle_transaction_email TEXT,
    lead_response_email TEXT,
    support_email TEXT,
    sales_email TEXT,
    raw_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organisation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organisation_id INTEGER NOT NULL,
    changed_at TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    organisation_id INTEGER,
    email TEXT,
    first_name TEXT,
    last_name TEXT,
    mobile TEXT,
    role TEXT,
    status TEXT,
    is_primary INTEGER,
    raw_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    order_number TEXT,
    order_type TEXT,
    order_status TEXT,
    service_number TEXT,
    product TEXT,
    speed TEXT,
    end_customer TEXT,
    external_reference TEXT,
    address TEXT,
    placed_by TEXT,
    customer_email TEXT,
    created_on TEXT,
    date_implemented TEXT,
    remark TEXT,
    message_for_isp TEXT,
    raw_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    service_number TEXT PRIMARY KEY,
    lifecycle TEXT NOT NULL, -- active | suspended | cancelled | unauthorized | unknown
    access_status TEXT,
    partner_status TEXT,
    download_kbps INTEGER,
    upload_kbps INTEGER,
    transport_type TEXT,
    circuit_type TEXT,
    customer TEXT,
    isp_name TEXT,
    address TEXT,
    can_be_accessed INTEGER,
    validator_message TEXT,
    circuit_admin TEXT,
    latest_order_id INTEGER,
    latest_order_status TEXT,
    raw_circuit_json TEXT,
    raw_status_json TEXT,
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    exclusive_status TEXT,
    suspend_started_at TEXT,
    last_restored_at TEXT,
    suspend_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS service_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_number TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    lifecycle TEXT,
    access_status TEXT,
    partner_status TEXT,
    download_kbps INTEGER,
    upload_kbps INTEGER,
    note TEXT
);

CREATE TABLE IF NOT EXISTS service_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_number TEXT NOT NULL,
    event_type TEXT NOT NULL,
    at TEXT NOT NULL,
    source TEXT,
    note TEXT,
    duration_days INTEGER
);

CREATE TABLE IF NOT EXISTS products (
    sku TEXT,
    name TEXT,
    status TEXT,
    gis_name TEXT,
    raw_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Current Openserve wholesale. Cost is letter × 1.15 (not VAT registered).
-- Retail is live sell or house markup rounded up to R99. Seeded from packages.py.
CREATE TABLE IF NOT EXISTS openserve_wholesale (
    sku TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    family TEXT,
    down INTEGER,
    up INTEGER,
    speed TEXT,
    cost_ex_vat REAL,
    cost REAL,
    cost_incl_vat REAL,
    cost_pre_april REAL,
    cost_pre_april_incl REAL,
    increase REAL,
    retail REAL,
    markup REAL,
    effective_from TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT,
    install REAL,
    recharge_3 REAL,
    recharge_7 REAL,
    recharge_14 REAL,
    recharge_30 REAL
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_number TEXT PRIMARY KEY,
    invoice_date TEXT,
    account_number TEXT,
    product_family TEXT,
    total REAL,
    vat REAL,
    source TEXT,
    filename TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL,
    service_number TEXT,
    end_customer TEXT,
    product TEXT,
    invoice_text TEXT,
    charge_amount REAL,
    currency TEXT,
    event_type TEXT,
    extra_kind TEXT,
    capacity TEXT,
    activation_date TEXT,
    charge_date TEXT,
    period_start TEXT,
    period_end TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    amount REAL,
    reference TEXT,
    source TEXT,
    matched_invoice TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS bank_tx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT,
    account_name TEXT,
    ours INTEGER NOT NULL DEFAULT 0,
    paid_on TEXT NOT NULL,
    amount REAL NOT NULL,
    balance REAL,
    description TEXT,
    source TEXT,
    filename TEXT
);

CREATE TABLE IF NOT EXISTS customer_invoices (
    invoice_number INTEGER PRIMARY KEY,
    invoice_date TEXT,
    service_number TEXT,
    customer TEXT,
    period TEXT,
    amount REAL,
    vat REAL,
    status TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS customer_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT,
    customer TEXT,
    amount REAL,
    note TEXT,
    source TEXT,
    statement_number INTEGER
);

CREATE TABLE IF NOT EXISTS customer_statements (
    statement_number INTEGER PRIMARY KEY,
    statement_date TEXT,
    customer TEXT,
    total_due REAL,
    source TEXT,
    filename TEXT
);

CREATE TABLE IF NOT EXISTS package_prices (
    key TEXT PRIMARY KEY,
    description TEXT,
    rate REAL,
    source TEXT
);

CREATE TABLE IF NOT EXISTS book_accounts (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    parent TEXT
);

CREATE TABLE IF NOT EXISTS book_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paid_on TEXT NOT NULL,
    payee TEXT,
    memo TEXT,
    payment REAL,
    deposit REAL,
    amount REAL NOT NULL,
    balance REAL,
    qb_type TEXT,
    account TEXT NOT NULL,
    source TEXT,
    filename TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_book_entries_dedup
    ON book_entries (
        paid_on,
        COALESCE(payee, ''),
        COALESCE(memo, ''),
        COALESCE(payment, 0),
        COALESCE(deposit, 0),
        COALESCE(balance, 0),
        account
    );

CREATE TABLE IF NOT EXISTS netcash_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_ref TEXT,
    service_number TEXT,
    amount REAL,
    action_date TEXT,
    result TEXT,
    batch_id TEXT,
    source TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_netcash_items_dedup
    ON netcash_items (
        COALESCE(account_ref, ''),
        COALESCE(action_date, ''),
        COALESCE(amount, 0),
        COALESCE(batch_id, ''),
        COALESCE(result, ''),
        COALESCE(source, '')
    );

CREATE TABLE IF NOT EXISTS mail_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT,
    mailbox TEXT,
    sent_on TEXT,
    kind TEXT,
    subject TEXT,
    account_number TEXT,
    invoice_number TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_service ON orders(service_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_services_lifecycle ON services(lifecycle);
CREATE INDEX IF NOT EXISTS idx_status_history_sn ON service_status_history(service_number, changed_at);
CREATE INDEX IF NOT EXISTS idx_service_events_sn ON service_events(service_number, at);
