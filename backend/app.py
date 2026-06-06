import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "phytoguard.db")
AGO_RULES_PATH  = "agro_rules.json"


# ─────────────────────────────────────────────
# Utilitaire : connexion SQLite
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
# Utilitaire : nettoyer le nom de la maladie
# ─────────────────────────────────────────────
def clean_maladie_name(maladie):
    """Nettoie le nom retourné par l'IA (ex: Tomato___Late_blight -> Late_blight)"""
    if not maladie:
        return maladie
    if '___' in maladie:
        return maladie.split('___')[1]
    return maladie


# ─────────────────────────────────────────────
# Utilitaire : charger les règles agronomiques
# ─────────────────────────────────────────────
def load_agro_rules():
    try:
        with open(AGO_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# ─────────────────────────────────────────────
# Route 1 : GET /
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
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


# ─────────────────────────────────────────────
# Route 2 : POST /diagnose
# ─────────────────────────────────────────────
@app.route("/diagnose", methods=["POST"])
def diagnose():
    data = request.get_json(silent=True)

    # ── Validation des champs obligatoires ──
    if not data:
        return jsonify({"erreur": "Corps JSON manquant"}), 400

    champs_requis = ["culture", "maladie", "confiance"]
    for champ in champs_requis:
        if champ not in data:
            return jsonify({"erreur": f"Champ obligatoire manquant : {champ}"}), 400

    culture         = data["culture"]
    maladie_raw     = data["maladie"]
    confiance       = float(data["confiance"])
    severite_bbch   = data.get("severite_bbch", 0) or 0
    surface_lesions = data.get("surface_lesions", 0) or 0

    # 🔧 NETTOYER LE NOM DE LA MALADIE
    maladie = clean_maladie_name(maladie_raw)

    print(f"[DEBUG] Maladie reçue : '{maladie_raw}' → nettoyée : '{maladie}'")

    # ── Récupération des règles depuis agro_rules.json ──
    rules = load_agro_rules()
    
    # Chercher d'abord la maladie exacte, puis essayer avec .lower() si nécessaire
    rule = rules.get(maladie, {})
    if not rule:
        # Essayer avec la version en minuscules
        maladie_lower = maladie.lower()
        for key in rules.keys():
            if key.lower() == maladie_lower:
                rule = rules.get(key, {})
                maladie = key  # Garder la bonne casse
                print(f"[DEBUG] Maladie trouvée avec casse différente : '{key}'")
                break
    
    # Appliquer la règle par culture ou règle par défaut
    rule_culture = rule.get(culture) or rule.get("*", {})

    # ── Comparaison avec le SEI (Seuil Économique d'Intervention) ──
    sei = rule_culture.get("sei", 10)

    if severite_bbch >= 4 or surface_lesions >= sei * 3:
        recommandation = rule_culture.get("recommandation_critique", "Stade épidémique — traitement urgent.")
        niveau_alerte  = "critique"
        alerte_sms     = True
    elif surface_lesions >= sei or severite_bbch >= 2:
        recommandation = rule_culture.get("recommandation_sur_sei", "Traitement curatif recommandé.")
        niveau_alerte  = "intervention"
        alerte_sms     = False
    else:
        recommandation = rule_culture.get("recommandation_sous_sei", "Surveiller à J+7.")
        niveau_alerte  = "surveillance"
        alerte_sms     = False

    produit            = rule_culture.get("produit")
    dose_g_l           = rule_culture.get("dose_g_l")
    delai_recolte      = rule_culture.get("delai_recolte")
    stade_phenologique = rule_culture.get("stade_phenologique", "Non spécifié")

    print(f"[DEBUG] Règle trouvée : produit={produit}, dose={dose_g_l}")

    # ── Insertion dans diagnostics ──
    conn = get_db()
    cursor = conn.execute(
        """
        INSERT INTO diagnostics
            (parcelle_id, culture, maladie, confiance, top3,
             severite_bbch, surface_lesions,
             recommandation, produit, dose_g_l, delai_recolte)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("parcelle_id"),
            culture,
            maladie,  # On utilise le nom nettoyé
            confiance,
            json.dumps(data.get("top3")),
            severite_bbch,
            surface_lesions,
            recommandation,
            produit,
            dose_g_l,
            delai_recolte,
        )
    )
    diagnostic_id = cursor.lastrowid

    # ── Insertion géolocalisation si fournie ──
    if data.get("latitude") and data.get("longitude"):
        conn.execute(
            """
            INSERT INTO geolocalisations (diagnostic_id, latitude, longitude)
            VALUES (?, ?, ?)
            """,
            (diagnostic_id, data["latitude"], data["longitude"])
        )

    conn.commit()
    conn.close()

    return jsonify({
        "statut"            : "ok",
        "diagnostic_id"     : diagnostic_id,
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


# ─────────────────────────────────────────────
# Route 3 : GET /history
# ─────────────────────────────────────────────
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

    resultats = [dict(row) for row in rows]
    return jsonify({
        "total"       : len(resultats),
        "diagnostics" : resultats
    })
    # ─────────────────────────────────────────────
# Route 4 : POST /predict (pour recevoir l'image)
# ─────────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    """Reçoit une photo, l'analyse avec l'IA et envoie à l'API du Membre C"""
    
    import os
    import requests
    
    # Récupérer l'image
    image = request.files.get('image')
    if not image:
        return jsonify({"erreur": "Aucune image fournie"}), 400
    
    # Sauvegarder temporairement
    image_path = "temp_image.jpg"
    image.save(image_path)
    
    # Importer le pipeline existant
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "integration"))
    from pipeline import capture_image, preprocess, inference
    
    # Analyser l'image
    img = capture_image(image_path)
    img_preprocessed = preprocess(img)
    results = inference(img_preprocessed)
    
    # Nettoyer les résultats
    top1 = results[0]
    parties = top1["maladie"].split("___")
    culture = parties[0].lower() if len(parties) > 0 else "inconnu"
    maladie = parties[1] if len(parties) > 1 else top1["maladie"]
    
    # Envoyer à l'API du Membre C
    MEMBRE_C_URL = "http://172.20.10.2:5000"  # ← IP de toi (Membre C)
    
    payload = {
        "culture": culture,
        "maladie": maladie,
        "confiance": float(top1["confiance"]),
        "surface_lesions": 25,
        "severite_bbch": 2
    }
    
    try:
        response = requests.post(f"{MEMBRE_C_URL}/diagnose", json=payload, timeout=10)
        if response.status_code == 201:
            agro_data = response.json()
        else:
            agro_data = {"erreur": f"HTTP {response.status_code}"}
    except Exception as e:
        agro_data = {"erreur": str(e)}
    
    # Nettoyer
    os.remove(image_path)
    
    return jsonify({
        "ia": results,
        "agro": agro_data
    })


# ─────────────────────────────────────────────
# Lancement
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)