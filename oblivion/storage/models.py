SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vault_items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    encrypted_payload TEXT NOT NULL,
    policy TEXT NOT NULL DEFAULT 'transfer_and_wipe',
    target_path TEXT,
    attachment_filename TEXT,
    attachment_path TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trusted_contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    telegram_chat_id TEXT,
    recovery_token_hash TEXT,
    public_instructions TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS item_assignments (
    item_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    encrypted_item_share TEXT NOT NULL,
    PRIMARY KEY (item_id, contact_id),
    FOREIGN KEY (item_id) REFERENCES vault_items (id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES trusted_contacts (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rate_limit_state (
    key TEXT PRIMARY KEY,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'INFO'
);
"""
