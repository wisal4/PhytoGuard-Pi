PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS parcelles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL,
    culture     TEXT    NOT NULL,
    superficie  REAL,
    notes       TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS diagnostics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    parcelle_id     INTEGER REFERENCES parcelles(id) ON DELETE SET NULL,
    culture         TEXT    NOT NULL,
    maladie         TEXT    NOT NULL,
    confiance       REAL    NOT NULL,
    top3            TEXT,
    severite_bbch   INTEGER,
    surface_lesions REAL,
    recommandation  TEXT,
    produit         TEXT,
    dose_g_l        REAL,
    delai_recolte   INTEGER,
    image_path      TEXT,
    rapport_pdf     TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS geolocalisations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    diagnostic_id   INTEGER NOT NULL REFERENCES diagnostics(id) ON DELETE CASCADE,
    latitude        REAL    NOT NULL,
    longitude       REAL    NOT NULL,
    altitude        REAL,
    precision_m     REAL,
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_diagnostics_parcelle ON diagnostics(parcelle_id);
CREATE INDEX IF NOT EXISTS idx_diagnostics_maladie  ON diagnostics(maladie);
CREATE INDEX IF NOT EXISTS idx_diagnostics_date     ON diagnostics(created_at);
CREATE INDEX IF NOT EXISTS idx_geoloc_diagnostic    ON geolocalisations(diagnostic_id);