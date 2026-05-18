import cv2
import numpy as np
import os
import sys
import sqlite3
import json

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from cv.pipeline_cv import apply_clahe, apply_grabcut, check_quality

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

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "phytoguard_int8.tflite")
DB_PATH    = os.path.join(os.path.dirname(__file__), "..", "backend", "phytoguard.db")

# ─── 1. CAPTURE + redimensionnement automatique ───────────────
def capture_image(image_path):
    # Bug fix 1 : accepter .jpeg et .jpg
    if not os.path.exists(image_path):
        jpeg_path = image_path.replace(".jpg", ".jpeg")
        if os.path.exists(jpeg_path):
            image_path = jpeg_path
        else:
            raise FileNotFoundError(f"Image introuvable : {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image introuvable : {image_path}")
    # Bug fix 2 : redimensionner si trop grande (évite Killed sur Pi)
    h, w = image.shape[:2]
    if w > 1024 or h > 1024:
        image = cv2.resize(image, (640, 480))
        print(f"[OK] Image redimensionnée : 640x480")
    print(f"[OK] Image chargée : {image.shape}")
    return image

# ─── 2. PRÉTRAITEMENT (pipeline de B) ─────────────────────────
def preprocess(image):
    nette, score = check_quality(image)
    if not nette:
        print(f"[ATTENTION] Image floue (score: {score:.2f})")
    image = apply_clahe(image)
    image, mask = apply_grabcut(image)
    image = cv2.resize(image, (224, 224))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = image.astype(np.float32) / 255.0
    image = np.expand_dims(image, axis=0)
    print(f"[OK] Prétraitement terminé : {image.shape}")
    return image

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
    output = interpreter.get_tensor(output_details[0]['index'])[0]
    top3_idx = np.argsort(output)[-3:][::-1]
    resultats = [
        {"maladie": CLASS_NAMES[i], "confiance": float(output[i])}
        for i in top3_idx
    ]
    print(f"[OK] Inférence réelle : {resultats[0]['maladie']}")
    return resultats

# ─── 4. SAUVEGARDE SQLite ─────────────────────────────────────
def save_to_db(resultats, image_path, latitude=None, longitude=None):
    conn = sqlite3.connect(DB_PATH)
    top1 = resultats[0]
    culture = top1["maladie"].split("___")[0]
    maladie = top1["maladie"].split("___")[1] if "___" in top1["maladie"] else top1["maladie"]
    cursor = conn.execute(
        """
        INSERT INTO diagnostics (culture, maladie, confiance, top3, image_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            culture,
            maladie,
            top1["confiance"],
            json.dumps(resultats),
            image_path,
        )
    )
    diagnostic_id = cursor.lastrowid
    if latitude and longitude:
        conn.execute(
            "INSERT INTO geolocalisations (diagnostic_id, latitude, longitude) VALUES (?, ?, ?)",
            (diagnostic_id, latitude, longitude)
        )
    conn.commit()
    conn.close()
    print(f"[OK] Diagnostic sauvegardé en base (id={diagnostic_id})")
    return diagnostic_id

# ─── 5. PIPELINE COMPLET ──────────────────────────────────────
def run_pipeline(image_path, latitude=None, longitude=None):
    image = capture_image(image_path)
    image_preprocessed = preprocess(image)
    resultats = inference(image_preprocessed)
    save_to_db(resultats, image_path, latitude, longitude)
    return resultats

if __name__ == "__main__":
    resultats = run_pipeline(
        "data/feuille_reelle1.jpg",
        latitude=34.0209,
        longitude=-6.8416
    )
    print("\n=== RÉSULTATS ===")
    for r in resultats:
        print(f"{r['maladie']} : {r['confiance']*100:.1f}%")