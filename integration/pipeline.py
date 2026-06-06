import cv2
import numpy as np
import os
import sys
import json
import requests  # ← AJOUT : pour appeler l'API Flask

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from cv.pipeline_cv import apply_clahe, apply_grabcut, check_quality

from cv.pipeline_cv import apply_clahe, apply_grabcut, check_quality, extract_hsv_features, extract_lbp_features

# ─── Import TFLite (compatible PC et Pi) ──────────────────────
try:
    from ai_edge_litert.interpreter import Interpreter as TFLiteInterpreter
    USE_LITERT = True
except ImportError:
    import tensorflow as tf
    USE_LITERT = False

CLASS_NAMES = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust",
    "Apple___healthy", "Blueberry___healthy", "Cherry___Powdery_mildew",
    "Cherry___healthy", "Corn___Cercospora_leaf_spot",
    "Corn___Common_rust", "Corn___Northern_Leaf_Blight", "Corn___healthy",
    "Grape___Black_rot", "Grape___Esca", "Grape___Leaf_blight",
    "Grape___healthy", "Orange___Haunglongbing", "Peach___Bacterial_spot",
    "Peach___healthy", "Pepper___Bacterial_spot", "Pepper___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy", "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight",
    "Tomato___Late_blight", "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot", "Tomato___Spider_mites",
    "Tomato___Target_Spot", "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus", "Tomato___healthy"
]

MODEL_PATH  = os.path.join(os.path.dirname(__file__), "..", "model", "phytoguard_int8.tflite")
FLASK_URL   = "http://172.20.10.2:5000"  # ← URL du backend Flask (Membre C)


# ─── 1. CAPTURE + redimensionnement automatique ───────────────
def capture_image(image_path):
    if not os.path.exists(image_path):
        jpeg_path = image_path.replace(".jpg", ".jpeg")
        if os.path.exists(jpeg_path):
            image_path = jpeg_path
        else:
            raise FileNotFoundError(f"Image introuvable : {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image introuvable : {image_path}")
    h, w = image.shape[:2]
    if w > 1024 or h > 1024:
        image = cv2.resize(image, (640, 480))
        print(f"[OK] Image redimensionnée : 640x480")
    print(f"[OK] Image chargée : {image.shape}")
    return image


# ─── 2. PRÉTRAITEMENT (pipeline de B) ─────────────────────────
def preprocess(image):
    # Qualité
    nette, score = check_quality(image)
    if not nette:
        print(f"[ATTENTION] Image floue (score: {score:.2f})")
    
    # Traitement B
    image_clahe = apply_clahe(image)
    image_grabcut, mask = apply_grabcut(image_clahe)
    
    # Extraire features de B (pour info)
    hsv = extract_hsv_features(image_grabcut)
    lbp = extract_lbp_features(image_grabcut)
    print(f"[OK] HSV dominant : {hsv[0]:.2f} | LBP dominant : {lbp.max():.3f}")
    
    # Préparer pour TFLite (D)
    image_resized = cv2.resize(image_grabcut, (224, 224))
    image_rgb = cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB)
    image_norm = image_rgb.astype(np.float32) / 255.0
    image_final = np.expand_dims(image_norm, axis=0)
    
    print(f"[OK] Prétraitement terminé : {image_final.shape}")
    return image_final

# ─── 3. INFÉRENCE (compatible PC et Pi) ───────────────────────
def inference(image):
    if USE_LITERT:
        interpreter = TFLiteInterpreter(model_path=MODEL_PATH)
    else:
        interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    interpreter.set_tensor(input_details[0]['index'], image)
    interpreter.invoke()
    output   = interpreter.get_tensor(output_details[0]['index'])[0]
    top3_idx = np.argsort(output)[-3:][::-1]
    resultats = [
        {"maladie": CLASS_NAMES[i], "confiance": float(output[i])}
        for i in top3_idx
    ]
    print(f"[OK] Inférence réelle : {resultats[0]['maladie']}")
    return resultats


# ─── 4. ENVOI AU BACKEND FLASK (Membre C) ─────────────────────
# MODIFICATION : au lieu d'écrire directement en SQLite,
# on appelle la route POST /diagnose du backend Flask.
# Cela déclenche automatiquement :
#   - La logique SEI (3 niveaux d'alerte)
#   - Les règles agronomiques (agro_rules.json)
#   - La recommandation du produit phytosanitaire
#   - L'alerte SMS Twilio si niveau critique
#   - La sauvegarde en base SQLite via Flask
def send_to_flask(resultats, image_path, surface_lesions=None,
                  latitude=None, longitude=None):
    """
    Envoie les résultats du diagnostic au backend Flask du Membre C.
    Retourne la réponse Flask avec recommandation, SEI, produit, etc.
    """
    top1    = resultats[0]
    parties = top1["maladie"].split("___")
    culture = parties[0].lower() if len(parties) > 0 else "inconnu"
    maladie = parties[1].lower() if len(parties) > 1 else top1["maladie"].lower()

    # Préparer le corps de la requête
    payload = {
        "culture"        : culture,
        "maladie"        : maladie,
        "confiance"      : top1["confiance"],
        "top3"           : resultats,
        "image_path"     : image_path,
    }

    # Ajouter surface lésions si fournie (pipeline Membre B)
    if surface_lesions is not None:
        payload["surface_lesions"] = surface_lesions

    # Ajouter GPS si disponible
    if latitude is not None and longitude is not None:
        payload["latitude"]  = latitude
        payload["longitude"] = longitude

    try:
        response = requests.post(
            f"{FLASK_URL}/diagnose",
            json=payload,
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            print(f"[OK] Diagnostic envoyé au backend Flask (id={data.get('diagnostic_id')})")
            print(f"[OK] Niveau alerte : {data.get('niveau_alerte')}")
            print(f"[OK] Recommandation : {data.get('recommandation')}")
            print(f"[OK] Produit : {data.get('produit')} | Dose : {data.get('dose_g_l')} g/L")
            if data.get('alerte_sms'):
                print("[ALERTE] 🚨 SMS envoyé — niveau critique !")
            return data
        else:
            print(f"[ERREUR] Flask a retourné : {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print("[ERREUR] Flask non disponible — vérifier que app.py tourne")
        return None


# ─── 5. PIPELINE COMPLET ──────────────────────────────────────
def run_pipeline(image_path, surface_lesions=None,
                 latitude=None, longitude=None):
    """
    Pipeline complet :
    1. Capture + redimensionnement
    2. Prétraitement OpenCV (Membre B)
    3. Inférence TFLite (Membre A)
    4. Envoi au backend Flask (Membre C) → SEI + recommandation + SMS
    """
    image              = capture_image(image_path)
    image_preprocessed = preprocess(image)
    resultats          = inference(image_preprocessed)
    reponse_flask      = send_to_flask(
        resultats,
        image_path,
        surface_lesions=surface_lesions,
        latitude=latitude,
        longitude=longitude
    )
    return resultats, reponse_flask


if __name__ == "__main__":
    resultats, reponse = run_pipeline(
        "data/feuille_reelle1.jpeg",
        surface_lesions=25.0,   # % surface atteinte (Membre B)
        latitude=34.0209,
        longitude=-6.8416
    )
    print("\n=== RÉSULTATS IA ===")
    for r in resultats:
        print(f"{r['maladie']} : {r['confiance']*100:.1f}%")

    if reponse:
        print("\n=== RECOMMANDATION BACKEND (Membre C) ===")
        print(f"Niveau alerte  : {reponse.get('niveau_alerte')}")
        print(f"Recommandation : {reponse.get('recommandation')}")
        print(f"Produit        : {reponse.get('produit')}")
        print(f"Dose           : {reponse.get('dose_g_l')} g/L")
        print(f"Délai récolte  : {reponse.get('delai_recolte')} jours")
        print(f"Alerte SMS     : {'OUI 🚨' if reponse.get('alerte_sms') else 'NON'}")