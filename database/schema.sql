# SQLite schema reserved for a later persistence backend.
# The MVP uses CSV + in-memory CommandCenter state.

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    disaster_type TEXT,
    description TEXT,
    severity INTEGER,
    people_affected INTEGER,
    medical_emergency INTEGER,
    accessibility TEXT,
    status TEXT,
    lat REAL,
    lon REAL,
    reported_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    category TEXT,
    message TEXT
);
