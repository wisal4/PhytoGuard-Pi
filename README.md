# PhytoGuard-Pi

Système de diagnostic phytosanitaire embarqué sur Raspberry Pi 5.
Détecte les maladies des plantes via caméra + IA, sans internet, sur le terrain.

## Membres et rôles

| Membre | Rôle principal |
|--------|----------------|
| A | IA / Modèles TFLite (EfficientNet, U-Net) |
| B | Vision par ordinateur (OpenCV, CLAHE, GrabCut) |
| C | Backend Flask + Base de données SQLite |
| D | Intégration Pi + GitHub |

## Installation

```bash
git clone https://github.com/wisal4/PhytoGuard-Pi.git
cd PhytoGuard-Pi
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Structure du projet

- /model       — modèles TFLite EfficientNet et U-Net
- /cv          — pipeline OpenCV (CLAHE, GrabCut, masque foliaire)
- /backend     — Flask, SQLite, agro_rules.json
- /integration — script principal Pi, PiCamera2
- /data        — datasets (non versionnés)
- /docs        — documentation technique et notes

## Objectifs MVP (avant juin)

| # | Fonctionnalité | Deadline |
|---|----------------|----------|
| 1 | Inférence TFLite sur Pi 5 (top-3) | Fin S2 |
| 2 | Pipeline complet photo → résultat écran | Fin S2 |
| 3 | Recommandation depuis agro_rules.json | Fin S3 |
| 4 | Rapport PDF automatique | Fin S3 |
| 5 | Segmentation U-Net + % surface lésions | Fin S3 |
| 6 | Optimisation MobileNetV2 légère | Fin S4 |