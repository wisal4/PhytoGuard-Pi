import json
import sqlite3
import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


from alerte_sms import envoyer_alerte_sms

from generate_rapport import generer_rapport
import generate_rapport as rapport_module
from pipeline import run_pipeline

app = Flask(__name__)

DB_PATH        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "phytoguard.db")
AGO_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "agro_rules.json")

HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PhytoGuard-Pi</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: #0d1b2a;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      font-family: Arial, sans-serif;
      padding: 20px;
    }
    h1 { color: #4CAF50; font-size: 2.8em; margin-bottom: 10px; text-align: center; }
    .subtitle { color: #aaaaaa; font-size: 1.1em; margin-bottom: 40px; text-align: center; }
    .card {
      background: #1a2a3a;
      border-radius: 20px;
      padding: 30px;
      width: 100%;
      max-width: 500px;
      margin-bottom: 20px;
      border: 1px solid #2E7D32;
    }
    .card h2 { color: #4CAF50; margin-bottom: 20px; font-size: 1.4em; text-align: center; }
    input[type="file"] { display: none; }
    .file-label {
      display: block; width: 100%; padding: 20px;
      background: #0d1b2a; border: 2px dashed #4CAF50;
      border-radius: 15px; color: #aaaaaa; text-align: center;
      cursor: pointer; font-size: 1.1em; margin-bottom: 20px;
    }
    .file-label.selected { border-color: #81C784; color: #81C784; }
    .btn {
      width: 100%; height: 80px; font-size: 1.6em;
      margin: 10px 0; border: none; border-radius: 20px;
      cursor: pointer; font-weight: bold;
    }
    .btn-green { background-color: #2e7d32; color: white; border: 3px solid #4CAF50; }
    .btn-blue  { background-color: #1565c0; color: white; border: 3px solid #2196F3; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .loader { display: none; text-align: center; color: #4CAF50; font-size: 1.2em; margin: 20px 0; }
    .result-row {
      display: flex; justify-content: space-between;
      padding: 8px 0; border-bottom: 1px solid #1a3a4a; color: #fff;
    }
    .result-label { color: #aaa; }
    .barre-container { margin: 5px 0 10px 0; }
    .barre { height: 12px; background: #1a3a4a; border-radius: 6px; overflow: hidden; }
    .barre-fill { height: 100%; background: #4CAF50; border-radius: 6px; }
    .alerte-surveillance { color: #4CAF50; font-weight: bold; }
    .alerte-intervention  { color: #FF9800; font-weight: bold; }
    .alerte-critique      { color: #F44336; font-weight: bold; }
    .hist-item {
      background: #0d1b2a; border-radius: 10px;
      padding: 12px; margin-bottom: 10px; border-left: 4px solid #4CAF50;
    }
    .hist-maladie { color: #4CAF50; font-weight: bold; }
    .hist-detail  { color: #aaa; font-size: 0.9em; margin-top: 4px; }
    .btn-pdf {
      margin-top: 8px; padding: 8px 16px;
      background: #2e7d32; color: white;
      border: none; border-radius: 8px;
      cursor: pointer; font-size: 0.9em; font-weight: bold;
    }
    .btn-pdf:hover { background: #1b5e20; }
  </style>
</head>
<body>

  <h1>&#127807; PhytoGuard-Pi</h1>
  <p class="subtitle">Systeme de diagnostic des maladies des plantes</p>

  <!-- Formulaire -->
  <div class="card">
    <h2>&#128247; Lancer un Diagnostic</h2>
    <label class="file-label" id="fileLabel" for="imageInput">
      &#128193; Choisir une photo de feuille
    </label>
    <input type="file" id="imageInput" accept="image/*" onchange="onFileSelected(this)">
    <button class="btn btn-green" id="btnAnalyser" onclick="lancerDiagnostic()" disabled>
      &#128300; Analyser
    </button>
  </div>

  <!-- Loader -->
  <div class="loader" id="loader">&#9203; Analyse en cours...</div>

  <!-- Resultat IA -->
  <div class="card" id="resultat-ia" style="display:none">
    <h2>&#129302; Resultat IA — Top 3</h2>
    <div id="top3-list"></div>
    <button class="btn-pdf" id="btnPdf" style="display:none" onclick="genererRapport()">
      &#128196; Generer Rapport PDF
    </button>
  </div>

  <!-- Resultat Agro -->
  <div class="card" id="resultat" style="display:none">
    <h2>&#127807; Diagnostic Agronomique</h2>
    <div class="result-row"><span class="result-label">Maladie</span><span id="res-maladie">-</span></div>
    <div class="result-row"><span class="result-label">Culture</span><span id="res-culture">-</span></div>
    <div class="result-row"><span class="result-label">Confiance IA</span><span id="res-confiance">-</span></div>
    <div class="result-row"><span class="result-label">Niveau alerte</span><span id="res-alerte">-</span></div>
    <div class="result-row"><span class="result-label">Recommandation</span><span id="res-recommandation" style="text-align:right;max-width:60%">-</span></div>
    <div class="result-row"><span class="result-label">Produit</span><span id="res-produit">-</span></div>
    <div class="result-row"><span class="result-label">Dose</span><span id="res-dose">-</span></div>
    <div class="result-row"><span class="result-label">Delai recolte</span><span id="res-delai">-</span></div>
  </div>

  <!-- Bouton historique -->
  <button class="btn btn-blue" style="max-width:500px;width:100%" onclick="voirHistorique()">
    &#128203; Voir Historique
  </button>

  <!-- Historique -->
  <div class="card" id="historique" style="display:none">
    <h2>&#128203; Historique des diagnostics</h2>
    <div id="hist-liste"></div>
  </div>

  <script>
    let dernierDiagnosticId = null;

    function onFileSelected(input) {
      const label = document.getElementById("fileLabel");
      const btn   = document.getElementById("btnAnalyser");
      if (input.files && input.files[0]) {
        label.textContent = "OK : " + input.files[0].name;
        label.classList.add("selected");
        btn.disabled = false;
      }
    }

    async function lancerDiagnostic() {
      const input = document.getElementById("imageInput");
      if (!input.files || !input.files[0]) return;

      document.getElementById("loader").style.display = "block";
      document.getElementById("resultat").style.display = "none";
      document.getElementById("resultat-ia").style.display = "none";
      document.getElementById("btnAnalyser").disabled = true;

      const formData = new FormData();
      formData.append("image", input.files[0]);

      try {
        const response = await fetch("/predict", {
          method: "POST",
          body: formData
        });
        const data = await response.json();
        if (data.erreur) {
          alert("Erreur : " + data.erreur);
          return;
        }
        afficherResultat(data);
        if (data.diagnostic_id) {
          dernierDiagnosticId = data.diagnostic_id;
          document.getElementById("btnPdf").style.display = "block";
        }
      } catch (err) {
        alert("Erreur : " + err.message);
      } finally {
        document.getElementById("loader").style.display = "none";
        document.getElementById("btnAnalyser").disabled = false;
      }
    }

    function afficherResultat(data) {
      const agro = data.agro || {};
      const ia   = data.ia  || [];

      const top3Div = document.getElementById("top3-list");
      top3Div.innerHTML = "";
      ia.forEach((r, i) => {
        const pct = (r.confiance * 100).toFixed(1);
        top3Div.innerHTML += `
          <div style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;color:${i===0?'#F44336':'#aaa'}">
              <span style="font-weight:${i===0?'bold':'normal'}">${r.maladie}</span>
              <span>${pct}%</span>
            </div>
            <div class="barre-container">
              <div class="barre">
                <div class="barre-fill" style="width:${pct}%;background:${i===0?'#F44336':'#4CAF50'}"></div>
              </div>
            </div>
          </div>`;
      });
      document.getElementById("resultat-ia").style.display = "block";

      document.getElementById("res-maladie").textContent        = agro.maladie || "-";
      document.getElementById("res-culture").textContent        = agro.culture || "-";
      document.getElementById("res-confiance").textContent      = ia[0] ? (ia[0].confiance*100).toFixed(1)+"%" : "-";
      document.getElementById("res-produit").textContent        = agro.produit || "-";
      document.getElementById("res-dose").textContent           = agro.dose_g_l ? agro.dose_g_l+" g/L" : "-";
      document.getElementById("res-delai").textContent          = agro.delai_recolte ? agro.delai_recolte+" jours" : "-";
      document.getElementById("res-recommandation").textContent = agro.recommandation || "-";

      const alerteEl = document.getElementById("res-alerte");
      alerteEl.textContent = agro.niveau_alerte || "-";
      alerteEl.className   = "alerte-" + (agro.niveau_alerte || "");

      document.getElementById("resultat").style.display = "block";
    }

    function genererRapport() {
      if (dernierDiagnosticId) {
        window.open("/rapport/" + dernierDiagnosticId, "_blank");
      } else {
        alert("Aucun diagnostic disponible.");
      }
    }

    async function voirHistorique() {
      const hist  = document.getElementById("historique");
      const liste = document.getElementById("hist-liste");

      if (hist.style.display === "block") {
        hist.style.display = "none";
        return;
      }

      liste.innerHTML = "<p style='color:#aaa'>Chargement...</p>";
      hist.style.display = "block";

      try {
        const response = await fetch("/history?limite=10");
        const data     = await response.json();

        if (data.diagnostics.length === 0) {
          liste.innerHTML = "<p style='color:#aaa'>Aucun diagnostic.</p>";
          return;
        }

        liste.innerHTML = "";
        data.diagnostics.forEach(d => {
          const div = document.createElement("div");
          div.className = "hist-item";
          div.innerHTML = `
            <div class="hist-maladie">${d.maladie||"-"} (${d.culture||"-"})</div>
            <div class="hist-detail">
              Confiance : ${d.confiance?(d.confiance*100).toFixed(1)+"%":"-"} |
              Produit : ${d.produit||"-"} |
              ${d.created_at?d.created_at.substring(0,16):"-"}
            </div>
            <button class="btn-pdf" onclick="window.open('/rapport/${d.id}', '_blank')">
              &#128196; Rapport PDF
            </button>`;
          liste.appendChild(div);
        });
      } catch (err) {
        liste.innerHTML = "<p style='color:#F44336'>Erreur : " + err.message + "</p>";
      }
    }
  </script>
</body>
</html>
"""

# ─── Utilitaires ──────────────────────────────────────────────
def load_agro_rules():
    try:
        with open(AGO_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_agro_rule(maladie_raw, culture):
    rules = load_agro_rules()
    maladie = maladie_raw.split("___")[1] if "___" in maladie_raw else maladie_raw
    mapping = {
        "late_blight"        : "mildiou",
        "early_blight"       : "septoriose",
        "leaf_mold"          : "mildiou",
        "septoria_leaf_spot" : "septoriose",
        "powdery_mildew"     : "oidium",
        "black_rot"          : "botrytis",
        "target_spot"        : "septoriose",
        "bacterial_spot"     : "septoriose",
        "spider_mites"       : "mildiou",
        "leaf_blight"        : "mildiou",
    }
    maladie_fr = mapping.get(maladie.lower(), "mildiou")
    rule = rules.get(maladie_fr, {})
    rule_culture = rule.get(culture) or rule.get("*", {})
    return maladie, rule_culture

# ─── Routes ───────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML)

@app.route("/predict", methods=["POST"])
def predict():
    try:
        image = request.files.get("image")
        if not image:
            return jsonify({"erreur": "Image manquante"}), 400

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "temp_upload.jpg")
        image.save(path)

        resultats_ia, reponse_flask = run_pipeline(path)
        top1 = resultats_ia[0]
        maladie_full = top1["maladie"]
        culture = maladie_full.split("___")[0] if "___" in maladie_full else "Tomato"

        if reponse_flask:
            agro = {
                "maladie"       : reponse_flask.get("maladie"),
                "culture"       : culture,
                "recommandation": reponse_flask.get("recommandation"),
                "niveau_alerte" : reponse_flask.get("niveau_alerte"),
                "produit"       : reponse_flask.get("produit"),
                "dose_g_l"      : reponse_flask.get("dose_g_l"),
                "delai_recolte" : reponse_flask.get("delai_recolte"),
            }
            diagnostic_id = reponse_flask.get("diagnostic_id")
            maladie_clean = reponse_flask.get("maladie", "inconnue")
            severite = reponse_flask.get("severite_bbch", 2) or 2
            surface  = reponse_flask.get("surface_lesions", 25.0) or 25.0
        else:
            maladie_clean, rule = get_agro_rule(maladie_full, culture.lower())
            recommandation = rule.get("recommandation_sous_sei", "Surveiller à J+7.")
            agro = {
                "maladie"       : maladie_clean,
                "culture"       : culture,
                "recommandation": recommandation,
                "niveau_alerte" : "surveillance",
                "produit"       : rule.get("produit"),
                "dose_g_l"      : rule.get("dose_g_l"),
                "delai_recolte" : rule.get("delai_recolte"),
            }
            severite = 2
            surface  = 25.0
            diagnostic_id = None
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.execute(
                    """INSERT INTO diagnostics
                    (culture, maladie, confiance, top3, recommandation, produit, dose_g_l, delai_recolte)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        culture, maladie_clean, top1["confiance"],
                        json.dumps(resultats_ia), recommandation,
                        rule.get("produit"), rule.get("dose_g_l"), rule.get("delai_recolte"),
                    )
                )
                diagnostic_id = cursor.lastrowid
                conn.commit()
                conn.close()
                print(f"[OK] Diagnostic sauvegardé (id={diagnostic_id})")
            except Exception as e:
                print(f"[ATTENTION] SQLite : {e}")

        # ── Alerte SMS ──
        try:
            from alerte_sms import envoyer_alerte_sms
            envoyer_alerte_sms(
                maladie     = maladie_clean,
                culture     = culture,
                severite    = severite,
                surface     = surface
            )
        except Exception as e:
            print(f"[ATTENTION] Alerte : {e}")

        return jsonify({"ia": resultats_ia, "agro": agro, "diagnostic_id": diagnostic_id})

    except Exception as e:
        print(f"[ERREUR predict] {e}")
        return jsonify({"erreur": str(e)}), 500
    
                                                                                                                                                                                                                                                                                                                                                                                              
@app.route("/history", methods=["GET"])
def history():
    limite = min(int(request.args.get("limite", 20)), 100)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM diagnostics ORDER BY created_at DESC LIMIT ?", (limite,)
    ).fetchall()
    conn.close()
    return jsonify({"total": len(rows), "diagnostics": [dict(r) for r in rows]})

@app.route("/rapport/<int:diagnostic_id>", methods=["GET"])
def rapport(diagnostic_id):
    try:
        output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", f"rapport_{diagnostic_id}.pdf")
        rapport_module.DB_PATH = DB_PATH
        path = generer_rapport(diagnostic_id, output_path=output)
        if path:
            return send_file(path, as_attachment=True, download_name=f"rapport_{diagnostic_id}.pdf")
        return jsonify({"erreur": "Diagnostic introuvable"}), 404
    except Exception as e:
        print(f"[ERREUR rapport] {e}")
        return jsonify({"erreur": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)