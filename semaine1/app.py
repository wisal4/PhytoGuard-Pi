"""
PhytoGuard-Pi | app.py
Membre C | Semaine 2 - Interface tactile ajoutée

Routes :
  GET  /           → interface tactile HTML
  POST /diagnose   → enregistrer un diagnostic
  GET  /history    → historique des diagnostics
  GET  /statut     → statut JSON de l'API
"""

import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

DB_PATH        = "phytoguard.db"
AGO_RULES_PATH = "agro_rules.json"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_agro_rules():
    try:
        with open(AGO_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# ── Route 1 : GET / → Interface tactile HTML ──
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# ── Route 2 : GET /statut → Statut JSON ──
@app.route("/statut", methods=["GET"])
def statut():
    return jsonify({
        "projet"  : "PhytoGuard-Pi",
        "version" : "0.1.0",
        "statut"  : "en ligne",
        "heure"   : datetime.now().isoformat(),
        "routes"  : [
            "POST /diagnose  → enregistrer un diagnostic",
            "GET  /history   → consulter l'historique",
        ]
    })


# ── Route 3 : POST /diagnose ──
@app.route("/diagnose", methods=["POST"])
def diagnose():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"erreur": "Corps JSON manquant"}), 400

    for champ in ["culture", "maladie", "confiance"]:
        if champ not in data:
            return jsonify({"erreur": f"Champ manquant : {champ}"}), 400

    culture         = data["culture"]
    maladie         = data["maladie"]
    confiance       = float(data["confiance"])
    severite_bbch   = data.get("severite_bbch", 0) or 0
    surface_lesions = data.get("surface_lesions", 0) or 0

    rules = load_agro_rules()
    rule  = rules.get(maladie, {}).get(culture) or rules.get(maladie, {}).get("*", {})

    sei = rule.get("sei", 10)
    if severite_bbch >= 4 or surface_lesions >= sei * 3:
        recommandation = rule.get("recommandation_critique", "Stade épidémique — traitement urgent.")
        niveau_alerte  = "critique"
        alerte_sms     = True
    elif surface_lesions >= sei or severite_bbch >= 2:
        recommandation = rule.get("recommandation_sur_sei", "Traitement curatif recommandé.")
        niveau_alerte  = "intervention"
        alerte_sms     = False
    else:
        recommandation = rule.get("recommandation_sous_sei", "Surveiller à J+7.")
        niveau_alerte  = "surveillance"
        alerte_sms     = False

    produit            = rule.get("produit")
    dose_g_l           = rule.get("dose_g_l")
    delai_recolte      = rule.get("delai_recolte")
    stade_phenologique = rule.get("stade_phenologique", "Non spécifié")

    conn   = get_db()
    cursor = conn.execute(
        """INSERT INTO diagnostics
           (parcelle_id, culture, maladie, confiance, top3,
            severite_bbch, surface_lesions,
            recommandation, produit, dose_g_l, delai_recolte)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (data.get("parcelle_id"), culture, maladie, confiance,
         json.dumps(data.get("top3")), severite_bbch, surface_lesions,
         recommandation, produit, dose_g_l, delai_recolte)
    )

    if data.get("latitude") and data.get("longitude"):
        conn.execute(
            "INSERT INTO geolocalisations (diagnostic_id, latitude, longitude) VALUES (?,?,?)",
            (cursor.lastrowid, data["latitude"], data["longitude"])
        )

    conn.commit()
    conn.close()

    return jsonify({
        "statut"            : "ok",
        "diagnostic_id"     : cursor.lastrowid,
        "maladie"           : maladie,
        "confiance"         : confiance,
        "stade_phenologique": stade_phenologique,
        "sei"               : sei,
        "surface_lesions"   : surface_lesions,
        "niveau_alerte"     : niveau_alerte,
        "alerte_sms"        : alerte_sms,
        "recommandation"    : recommandation,
        "produit"           : produit,
        "dose_g_l"          : dose_g_l,
        "delai_recolte"     : delai_recolte,
    }), 201


# ── Route 4 : GET /history ──
@app.route("/history", methods=["GET"])
def history():
    limite  = min(int(request.args.get("limite", 20)), 100)
    culture = request.args.get("culture")
    maladie = request.args.get("maladie")

    query  = "SELECT * FROM diagnostics WHERE 1=1"
    params = []

    if culture:
        query  += " AND culture = ?"
        params.append(culture)
    if maladie:
        query  += " AND maladie = ?"
        params.append(maladie)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limite)

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify({
        "total"       : len(rows),
        "diagnostics" : [dict(r) for r in rows]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)