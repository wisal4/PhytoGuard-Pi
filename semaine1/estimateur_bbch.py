"""
PhytoGuard-Pi | estimateur_bbch.py
Membre C | Semaine 4

Estimateur de sévérité BBCH (5 niveaux : 0 à 4)
Combine :
  - % surface foliaire atteinte (du pipeline OpenCV - Membre B)
  - Score de confiance du modèle IA (du modèle TFLite - Membre A)
  - Couleur HSV (ratio jaunissement/brunissement)
  - Historique temporel de la parcelle

Échelle BBCH :
  0 = Sain        (0%)
  1 = Léger       (1-10%)
  2 = Modéré      (10-25%)
  3 = Sévère      (25-50%)
  4 = Épidémique  (>50%)
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "phytoguard.db"

# ─────────────────────────────────────────────
# Constantes BBCH
# ─────────────────────────────────────────────
SEUILS_BBCH = [
    (0,  0,    "Sain",       "🟢", "Aucun symptôme visible. Pas d'action nécessaire."),
    (1,  10,   "Léger",      "🟡", "Premiers symptômes. Surveiller à J+7."),
    (2,  25,   "Modéré",     "🟠", "Atteinte modérée. Traitement préventif recommandé."),
    (3,  50,   "Sévère",     "🔴", "Atteinte sévère. Traitement curatif urgent."),
    (4,  100,  "Épidémique", "🚨", "Stade épidémique. Alerte SMS. Traitement d'urgence."),
]


# ─────────────────────────────────────────────
# Calcul du niveau BBCH
# ─────────────────────────────────────────────
def calculer_bbch(surface_lesions, confiance=1.0, ratio_hsv=None, historique=None):
    """
    Calcule le niveau BBCH (0-4) selon plusieurs indicateurs.

    Args:
        surface_lesions (float) : % surface foliaire atteinte (0-100)
        confiance       (float) : score de confiance du modèle IA (0-1)
        ratio_hsv       (float) : ratio jaunissement/brunissement HSV (optionnel)
        historique      (list)  : liste des sévérités précédentes (optionnel)

    Returns:
        dict : niveau, label, emoji, description, score_final
    """

    # ── Score de base selon surface lésions ──
    score_surface = surface_lesions  # 0 à 100

    # ── Ajustement selon confiance IA ──
    # Si confiance faible → on réduit légèrement le score
    facteur_confiance = 0.7 + (confiance * 0.3)
    score_ajuste = score_surface * facteur_confiance

    # ── Ajustement selon ratio HSV (jaunissement/brunissement) ──
    if ratio_hsv is not None:
        # ratio_hsv > 0.5 → beaucoup de jaunissement → aggrave le score
        bonus_hsv = (ratio_hsv - 0.5) * 10
        score_ajuste += max(0, bonus_hsv)

    # ── Ajustement selon historique (tendance) ──
    if historique and len(historique) >= 2:
        tendance = historique[-1] - historique[-2]
        if tendance > 0:
            # Aggravation → +5% au score
            score_ajuste += 5
        elif tendance < 0:
            # Amélioration → -3% au score
            score_ajuste -= 3

    score_final = min(100, max(0, score_ajuste))

    # ── Détermination du niveau BBCH ──
    niveau = 0
    for niv, seuil_max, label, emoji, description in SEUILS_BBCH:
        if score_final <= seuil_max or niv == 4:
            niveau = niv
            break

    _, _, label, emoji, description = SEUILS_BBCH[niveau]

    return {
        "niveau_bbch"    : niveau,
        "label"          : label,
        "emoji"          : emoji,
        "description"    : description,
        "score_final"    : round(score_final, 1),
        "surface_entree" : surface_lesions,
        "confiance_ia"   : confiance,
        "alerte_sms"     : niveau >= 4,
    }


# ─────────────────────────────────────────────
# Récupérer l'historique d'une parcelle
# ─────────────────────────────────────────────
def get_historique(culture, maladie, limite=5):
    """Récupère les dernières sévérités BBCH pour une culture/maladie."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """SELECT severite_bbch FROM diagnostics
               WHERE culture = ? AND maladie = ?
               AND severite_bbch IS NOT NULL
               ORDER BY created_at DESC LIMIT ?""",
            (culture, maladie, limite)
        ).fetchall()
        conn.close()
        return [r[0] for r in rows][::-1]  # ordre chronologique
    except:
        return []


# ─────────────────────────────────────────────
# Sauvegarder le niveau BBCH en base
# ─────────────────────────────────────────────
def sauvegarder_bbch(diagnostic_id, niveau_bbch):
    """Met à jour le niveau BBCH d'un diagnostic en base."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE diagnostics SET severite_bbch = ? WHERE id = ?",
            (niveau_bbch, diagnostic_id)
        )
        conn.commit()
        conn.close()
        print(f"[OK] Diagnostic #{diagnostic_id} → BBCH niveau {niveau_bbch} sauvegardé")
    except Exception as e:
        print(f"[ERREUR] {e}")


# ─────────────────────────────────────────────
# Affichage du résultat
# ─────────────────────────────────────────────
def afficher_resultat(resultat):
    print("\n" + "="*50)
    print("  ESTIMATEUR DE SÉVÉRITÉ BBCH — PhytoGuard-Pi")
    print("="*50)
    print(f"  Niveau BBCH    : {resultat['niveau_bbch']} / 4")
    print(f"  Sévérité       : {resultat['emoji']} {resultat['label']}")
    print(f"  Score final    : {resultat['score_final']} %")
    print(f"  Surface entrée : {resultat['surface_entree']} %")
    print(f"  Confiance IA   : {resultat['confiance_ia'] * 100:.1f} %")
    print(f"  Action         : {resultat['description']}")
    print(f"  Alerte SMS     : {'🚨 OUI' if resultat['alerte_sms'] else '✅ NON'}")
    print("="*50 + "\n")


# ─────────────────────────────────────────────
# Tests des 5 niveaux
# ─────────────────────────────────────────────
def tester_tous_niveaux():
    """Teste les 5 niveaux BBCH avec des cas réels."""
    print("\n🧪 TEST DES 5 NIVEAUX BBCH\n")

    cas_tests = [
        {"surface": 0,   "confiance": 0.95, "label_attendu": "Sain"},
        {"surface": 5,   "confiance": 0.88, "label_attendu": "Léger"},
        {"surface": 18,  "confiance": 0.92, "label_attendu": "Modéré"},
        {"surface": 35,  "confiance": 0.85, "label_attendu": "Sévère"},
        {"surface": 65,  "confiance": 0.90, "label_attendu": "Épidémique"},
    ]

    for i, cas in enumerate(cas_tests):
        print(f"--- Cas {i+1} : surface={cas['surface']}%, confiance={cas['confiance']} ---")
        resultat = calculer_bbch(
            surface_lesions=cas["surface"],
            confiance=cas["confiance"]
        )
        afficher_resultat(resultat)

        # Validation
        if resultat["label"] == cas["label_attendu"]:
            print(f"  ✅ Test {i+1} VALIDÉ : {resultat['label']}\n")
        else:
            print(f"  ⚠️  Test {i+1} : attendu {cas['label_attendu']}, obtenu {resultat['label']}\n")


# ─────────────────────────────────────────────
# Programme principal
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Test des 5 niveaux
    tester_tous_niveaux()

    # Test avec historique
    print("\n📈 TEST AVEC HISTORIQUE (tendance aggravante)\n")
    historique_test = [0, 1, 1, 2, 3]  # tendance à la hausse
    resultat = calculer_bbch(
        surface_lesions=20,
        confiance=0.90,
        historique=historique_test
    )
    afficher_resultat(resultat)
    print(f"Note : historique {historique_test} → tendance aggravante détectée\n")