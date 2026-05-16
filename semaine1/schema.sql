-- PhytoGuard-Pi | Schema SQLite
-- Membre C | Semaine 1
-- Tables : parcelles, diagnostics, geolocalisations

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────
-- Table 1 : parcelles
-- Représente un champ / une parcelle agricole
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS parcelles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL,               -- ex: "Parcelle blé nord"
    culture     TEXT    NOT NULL,               -- ex: "blé", "vigne", "tomate"
    superficie  REAL,                           -- en hectares (optionnel)
    notes       TEXT,                           -- remarques libres
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────
-- Table 2 : diagnostics
-- Un diagnostic = une analyse d'une feuille
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS diagnostics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    parcelle_id     INTEGER REFERENCES parcelles(id) ON DELETE SET NULL,
    culture         TEXT    NOT NULL,           -- culture analysée
    maladie         TEXT    NOT NULL,           -- nom de la maladie détectée
    confiance       REAL    NOT NULL,           -- score top-1 (0.0 à 1.0)
    top3            TEXT,                       -- JSON: [{"maladie":..., "score":...}, ...]
    severite_bbch   INTEGER,                    -- niveau 0-4 (0=sain, 4=épidémique)
    surface_lesions REAL,                       -- % surface foliaire atteinte
    recommandation  TEXT,                       -- texte de la recommandation agro
    produit         TEXT,                       -- produit phytosanitaire recommandé
    dose_g_l        REAL,                       -- dose en g/L
    delai_recolte   INTEGER,                    -- jours avant récolte autorisée
    image_path      TEXT,                       -- chemin image annotée (local)
    rapport_pdf     TEXT,                       -- chemin rapport PDF généré
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────
-- Table 3 : geolocalisations
-- Coordonnées GPS optionnelles par diagnostic
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS geolocalisations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    diagnostic_id   INTEGER NOT NULL REFERENCES diagnostics(id) ON DELETE CASCADE,
    latitude        REAL    NOT NULL,
    longitude       REAL    NOT NULL,
    altitude        REAL,                       -- en mètres (optionnel)
    precision_m     REAL,                       -- précision GPS en mètres
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────
-- Index utiles pour les requêtes fréquentes
-- ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_diagnostics_parcelle  ON diagnostics(parcelle_id);
CREATE INDEX IF NOT EXISTS idx_diagnostics_maladie   ON diagnostics(maladie);
CREATE INDEX IF NOT EXISTS idx_diagnostics_date      ON diagnostics(created_at);
CREATE INDEX IF NOT EXISTS idx_geoloc_diagnostic     ON geolocalisations(diagnostic_id);