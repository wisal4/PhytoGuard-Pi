# 🌱 PhytoGuard-Pi

**Système de diagnostic phytosanitaire autonome sur Raspberry Pi 4**

> Classification des maladies foliaires par deep learning optimisé, quantification des lésions et recommandations agronomiques en temps réel.

---

## 📋 Description

PhytoGuard-Pi est un outil portable et autonome capable de :
- Identifier **38 maladies** sur **14 cultures** différentes (tomate, maïs, vigne, blé, pomme de terre, etc.)
- Analyser une feuille en **moins de 3 secondes**
- Atteindre un taux de précision **supérieur à 94%**
- Fonctionner **6 heures sur batterie** sur le terrain
- Envoyer des **alertes SMS** automatiques en cas d'épidémie

---

## 👥 Équipe

| Membre | Rôle principal | Tâches |
|--------|---------------|--------|
| **A** | IA / Modèles | EfficientNet-B0, U-Net, TFLite, optimisation |
| **B** | Vision (CV) | Pipeline OpenCV, segmentation, NDVI |
| **C** | Backend | Flask, SQLite, PDF, SMS, interface tactile |
| **D** | Intégration Pi | Pipeline complet, UI, batterie, démo |

---

## 🏗️ Architecture

```
PhytoGuard-Pi/
├── semaine1/
│   ├── app.py                  # Serveur Flask (Membre C)
│   ├── schema.sql              # Schéma base SQLite (Membre C)
│   ├── init_db.py              # Initialisation base (Membre C)
│   ├── agro_rules.json         # Règles agronomiques (Membre C)
│   ├── generate_rapport.py     # Génération PDF (Membre C)
│   ├── estimateur_bbch.py      # Estimateur sévérité (Membre C)
│   ├── alerte_sms.py           # Alertes SMS Twilio (Membre C)
│   └── templates/
│       └── index.html          # Interface tactile (Membre C)
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation sur Raspberry Pi

### Étape 1 — Prérequis système

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-opencv sqlite3 -y
```

### Étape 2 — Cloner le projet

```bash
git clone https://github.com/wisal4/PhytoGuard-Pi.git
cd PhytoGuard-Pi
```

### Étape 3 — Installer les dépendances

```bash
pip install -r requirements.txt --break-system-packages
```

### Étape 4 — Initialiser la base de données

```bash
cd semaine1
python init_db.py
```

Résultat attendu :
```
[OK] Base de données initialisée : phytoguard.db
[OK] Tables présentes : ['diagnostics', 'geolocalisations', 'parcelles']
```

### Étape 5 — Configurer Twilio (optionnel)

Ouvrir `alerte_sms.py` et renseigner :
```python
ACCOUNT_SID   = "votre_account_sid"
AUTH_TOKEN    = "votre_auth_token"
TWILIO_NUMBER = "votre_numero_twilio"
MON_NUMERO    = "votre_numero_personnel"
```

### Étape 6 — Lancer le serveur Flask

```bash
python app.py
```

Accéder à l'interface sur : `http://127.0.0.1:5000`

---

## 🗄️ Base de données SQLite

### Tables

**`parcelles`** — Champs agricoles enregistrés
```sql
id, nom, culture, superficie, notes, created_at
```

**`diagnostics`** — Chaque analyse effectuée
```sql
id, parcelle_id, culture, maladie, confiance, top3,
severite_bbch, surface_lesions, recommandation,
produit, dose_g_l, delai_recolte, image_path,
rapport_pdf, created_at
```

**`geolocalisations`** — Coordonnées GPS
```sql
id, diagnostic_id, latitude, longitude, altitude, precision_m, created_at
```

---

## 🌐 API REST Flask

### GET /
Affiche l'interface tactile HTML.

### GET /statut
Retourne le statut JSON de l'API.
```json
{
  "projet": "PhytoGuard-Pi",
  "version": "0.1.0",
  "statut": "en ligne"
}
```

### POST /diagnose
Enregistre un diagnostic et retourne la recommandation.

**Corps JSON :**
```json
{
  "culture": "tomate",
  "maladie": "mildiou",
  "confiance": 0.92,
  "severite_bbch": 2,
  "surface_lesions": 25.0,
  "parcelle_id": 1,
  "latitude": 34.01,
  "longitude": -5.00
}
```

**Réponse :**
```json
{
  "diagnostic_id": 1,
  "niveau_alerte": "intervention",
  "alerte_sms": false,
  "recommandation": "Traitement curatif recommandé.",
  "produit": "Mancozèbe",
  "dose_g_l": 2.0,
  "delai_recolte": 7
}
```

### GET /history
Retourne l'historique des diagnostics.

**Paramètres optionnels :** `?limite=20&culture=tomate&maladie=mildiou`

---

## 📊 Logique SEI (Seuil Économique d'Intervention)

| Condition | Niveau | Alerte SMS | Action |
|-----------|--------|-----------|--------|
| surface < SEI ET bbch < 2 | surveillance | NON | Surveiller à J+7 |
| surface ≥ SEI OU bbch ≥ 2 | intervention | NON | Traitement curatif |
| surface ≥ SEI×3 OU bbch = 4 | critique | **OUI** | Traitement urgent |

---

## 🌿 Règles agronomiques

5 maladies prioritaires avec SEI et stade phénologique :

| Maladie | SEI (%) | Produit | Délai récolte |
|---------|---------|---------|---------------|
| Mildiou | 5-15 | Mancozèbe | 7-21 j |
| Oïdium | 5-15 | Soufre mouillable | 3-35 j |
| Septoriose | 20-30 | Propiconazole | 7-35 j |
| Botrytis | 5 | Iprodione | 7-14 j |
| Rouille | 5-10 | Tébuconazole | 3-35 j |

---

## 📈 Estimateur BBCH

| Niveau | Label | Surface lésions | Action |
|--------|-------|----------------|--------|
| 0 | 🟢 Sain | 0% | Aucune action |
| 1 | 🟡 Léger | 1-10% | Surveiller à J+7 |
| 2 | 🟠 Modéré | 10-25% | Traitement préventif |
| 3 | 🔴 Sévère | 25-50% | Traitement curatif urgent |
| 4 | 🚨 Épidémique | >50% | Traitement d'urgence + SMS |

---

## 📄 Génération rapport PDF

```bash
python generate_rapport.py
```

Le PDF est généré dans `rapports/rapport_<id>_<date>.pdf` avec :
- Informations du diagnostic
- Maladie et sévérité BBCH
- Recommandation agronomique
- Tableau du traitement
- Graphique d'évolution

---

## 🛠️ Stack technique

```
Python 3.11+, Flask 3.1, SQLite3
TensorFlow 2.14 / TFLite, OpenCV 4.9
ReportLab, Pillow, Twilio
Raspberry Pi 4 (4 Go), PiCamera Module 3 AF
Écran tactile 7 pouces, Batterie LiPo 10 000 mAh
```

---

## 📜 Licence

Projet académique — INPT 2026