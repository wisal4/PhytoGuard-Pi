
import sqlite3
import os

DB_PATH     = "phytoguard.db"
SCHEMA_PATH = "schema.sql"


def init_db():
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Fichier schéma introuvable : {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.commit()
    conn.close()

    print(f"[OK] Base de données initialisée : {DB_PATH}")


def verify_db():
    """Vérifie que les tables existent bien."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    expected = {"diagnostics", "geolocalisations", "parcelles"}
    found    = set(tables)

    if expected.issubset(found):
        print(f"[OK] Tables présentes : {sorted(found)}")
    else:
        manquantes = expected - found
        print(f"[ERREUR] Tables manquantes : {manquantes}")


if __name__ == "__main__":
    init_db()
    verify_db()