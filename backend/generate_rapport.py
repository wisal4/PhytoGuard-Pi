"""
PhytoGuard-Pi | generate_rapport.py
Membre C | Semaine 3

Génère un rapport PDF automatique pour chaque diagnostic :
- Photo annotée (ou placeholder)
- Maladie détectée + confiance
- Sévérité BBCH
- Recommandation de traitement
- Graphique d'évolution des diagnostics
"""

import sqlite3
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

DB_PATH = "phytoguard.db"

# ─────────────────────────────────────────────
# Couleurs PhytoGuard
# ─────────────────────────────────────────────
VERT      = colors.HexColor("#2E7D32")
VERT_CLAIR= colors.HexColor("#C8E6C9")
ROUGE     = colors.HexColor("#C62828")
ORANGE    = colors.HexColor("#E65100")
JAUNE     = colors.HexColor("#F9A825")
BLEU      = colors.HexColor("#1565C0")
GRIS      = colors.HexColor("#F5F5F5")
BLANC     = colors.white
NOIR      = colors.HexColor("#212121")

# ─────────────────────────────────────────────
# Couleur selon niveau d'alerte
# ─────────────────────────────────────────────
def couleur_alerte(severite):
    if severite is None or severite == 0:
        return VERT
    elif severite == 1:
        return JAUNE
    elif severite == 2:
        return ORANGE
    else:
        return ROUGE

def label_bbch(severite):
    labels = {
        0: "Sain (0)",
        1: "Léger (1)",
        2: "Modéré (2)",
        3: "Sévère (3)",
        4: "Épidémique (4)"
    }
    return labels.get(severite, "Inconnu")

# ─────────────────────────────────────────────
# Graphique d'évolution (barres simples)
# ─────────────────────────────────────────────
def creer_graphique_evolution(historique):
    """Crée un graphique en barres de l'évolution des sévérités."""
    if not historique:
        return None

    w, h = 14*cm, 5*cm
    d = Drawing(w, h)

    # Fond
    d.add(Rect(0, 0, w, h, fillColor=GRIS, strokeColor=colors.HexColor("#CCCCCC"), strokeWidth=0.5))

    n = min(len(historique), 10)
    recent = historique[-n:]
    bar_w = (w - 2*cm) / n
    max_val = 4

    for i, row in enumerate(recent):
        sev = row["severite_bbch"] or 0
        bar_h = (sev / max_val) * (h - 1.5*cm)
        x = 1*cm + i * bar_w + bar_w * 0.1
        y = 0.8*cm
        bw = bar_w * 0.8
        couleur = couleur_alerte(sev)
        d.add(Rect(x, y, bw, max(bar_h, 0.1*cm),
                   fillColor=couleur, strokeColor=BLANC, strokeWidth=0.5))
        # Date courte
        date_str = str(row["created_at"])[:10] if row["created_at"] else ""
        d.add(String(x + bw/2, 0.2*cm, date_str[-5:],
                     fontSize=5, textAnchor='middle', fillColor=NOIR))

    # Ligne de référence SEI
    sei_y = 0.8*cm + (2/4) * (h - 1.5*cm)
    d.add(Line(0.5*cm, sei_y, w - 0.5*cm, sei_y,
               strokeColor=ORANGE, strokeWidth=1, strokeDashArray=[3, 3]))
    d.add(String(w - 0.4*cm, sei_y + 0.1*cm, "SEI",
                 fontSize=6, textAnchor='end', fillColor=ORANGE))

    return d

# ─────────────────────────────────────────────
# Génération du rapport PDF
# ─────────────────────────────────────────────
def generer_rapport(diagnostic_id, output_path=None):
    """Génère un rapport PDF pour un diagnostic donné."""

    # ── Lecture en base ──
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    diag = conn.execute(
        "SELECT * FROM diagnostics WHERE id = ?", (diagnostic_id,)
    ).fetchone()

    if not diag:
        print(f"[ERREUR] Diagnostic {diagnostic_id} introuvable.")
        conn.close()
        return None

    # Historique de la même culture/maladie
    historique = conn.execute(
        """SELECT severite_bbch, created_at FROM diagnostics
           WHERE culture = ? AND maladie = ?
           ORDER BY created_at ASC LIMIT 10""",
        (diag["culture"], diag["maladie"])
    ).fetchall()

    conn.close()

    # ── Chemin du PDF ──
    os.makedirs("rapports", exist_ok=True)
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"rapports/rapport_{diagnostic_id}_{ts}.pdf"

    # ── Styles ──
    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle(
        "titre", parent=styles["Title"],
        fontSize=22, textColor=VERT, spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    style_sous_titre = ParagraphStyle(
        "sous_titre", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#555555"),
        spaceAfter=4, fontName="Helvetica"
    )
    style_section = ParagraphStyle(
        "section", parent=styles["Heading2"],
        fontSize=13, textColor=BLEU, spaceBefore=14, spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    style_normal = ParagraphStyle(
        "normal", parent=styles["Normal"],
        fontSize=10, leading=14, fontName="Helvetica"
    )
    style_alerte = ParagraphStyle(
        "alerte", parent=styles["Normal"],
        fontSize=11, leading=15, fontName="Helvetica-Bold",
        textColor=couleur_alerte(diag["severite_bbch"])
    )

    # ── Construction du document ──
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm
    )

    story = []
    W = A4[0] - 4*cm  # largeur utile

    # ── En-tête ──
    story.append(Paragraph("🌱 PhytoGuard-Pi", style_titre))
    story.append(Paragraph("Rapport de diagnostic phytosanitaire automatique", style_sous_titre))
    story.append(HRFlowable(width=W, thickness=2, color=VERT, spaceAfter=12))

    # ── Infos générales ──
    date_str = str(diag["created_at"])[:19] if diag["created_at"] else datetime.now().isoformat()[:19]
    info_data = [
        ["Diagnostic N°", f"#{diag['id']}",
         "Date", date_str],
        ["Culture", diag["culture"].capitalize(),
         "Parcelle", f"#{diag['parcelle_id']}" if diag["parcelle_id"] else "Non spécifiée"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), VERT_CLAIR),
        ("BACKGROUND", (2, 0), (2, -1), VERT_CLAIR),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUND", (0, 1), (-1, 1), GRIS),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Maladie détectée ──
    story.append(Paragraph("Maladie détectée", style_section))
    confiance_pct = round(diag["confiance"] * 100, 1) if diag["confiance"] else 0
    maladie_data = [
        ["Maladie", diag["maladie"].capitalize()],
        ["Confiance IA", f"{confiance_pct} %"],
        ["Sévérité BBCH", label_bbch(diag["severite_bbch"])],
        ["Surface lésions", f"{diag['surface_lesions']} %" if diag["surface_lesions"] else "Non calculée"],
    ]
    maladie_table = Table(maladie_data, colWidths=[4*cm, 12*cm])
    maladie_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), VERT_CLAIR),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUND", (0, 1), (-1, 1), GRIS),
        ("ROWBACKGROUND", (0, 3), (-1, 3), GRIS),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("TEXTCOLOR", (1, 2), (1, 2), couleur_alerte(diag["severite_bbch"])),
        ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),
    ]))
    story.append(maladie_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Recommandation ──
    story.append(Paragraph("Recommandation agronomique", style_section))
    recommandation = diag["recommandation"] or "Consulter un agronome."
    story.append(Paragraph(f"<b>Action :</b> {recommandation}", style_alerte))
    story.append(Spacer(1, 0.3*cm))

    # Tableau traitement
    if diag["produit"]:
        trait_data = [
            ["Produit recommandé", "Dose (g/L)", "Délai avant récolte", "Méthode"],
            [
                diag["produit"] or "-",
                f"{diag['dose_g_l']} g/L" if diag["dose_g_l"] else "-",
                f"{diag['delai_recolte']} jours" if diag["delai_recolte"] else "-",
                "Pulvérisation foliaire"
            ]
        ]
        trait_table = Table(trait_data, colWidths=[4*cm, 3*cm, 4*cm, 5*cm])
        trait_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), VERT),
            ("TEXTCOLOR", (0, 0), (-1, 0), BLANC),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("BACKGROUND", (0, 1), (-1, 1), GRIS),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(trait_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Graphique d'évolution ──
    story.append(Paragraph("Evolution de la maladie (10 derniers diagnostics)", style_section))
    graphique = creer_graphique_evolution(historique)
    if graphique:
        story.append(graphique)
    story.append(Paragraph(
        "La ligne pointillee orange represente le Seuil Economique d'Intervention (SEI).",
        ParagraphStyle("note", parent=styles["Normal"],
                       fontSize=8, textColor=colors.HexColor("#777777"),
                       fontName="Helvetica-Oblique")
    ))
    story.append(Spacer(1, 0.4*cm))

    # ── Pied de page ──
    story.append(HRFlowable(width=W, thickness=1, color=VERT_CLAIR, spaceBefore=8))
    story.append(Paragraph(
        f"Rapport genere automatiquement par PhytoGuard-Pi v0.1.0 | {date_str}",
        ParagraphStyle("footer", parent=styles["Normal"],
                       fontSize=8, textColor=colors.HexColor("#999999"),
                       fontName="Helvetica", alignment=1)
    ))

    # ── Génération ──
    doc.build(story)
    print(f"[OK] Rapport PDF généré : {output_path}")
    return output_path


# ─────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Génère un rapport pour le dernier diagnostic en base
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    derniers = conn.execute(
        "SELECT id FROM diagnostics ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if derniers:
        generer_rapport(derniers["id"])
    else:
        print("[INFO] Aucun diagnostic en base. Lance d'abord app.py et POST /diagnose.")