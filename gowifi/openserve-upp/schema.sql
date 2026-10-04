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

CREATE INDEX IF NOT EXISTS idx_orders_service ON orders(service_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_services_lifecycle ON services(lifecycle);
CREATE INDEX IF NOT EXISTS idx_status_history_sn ON service_status_history(service_number, changed_at);
CREATE INDEX IF NOT EXISTS idx_service_events_sn ON service_events(service_number, at);
