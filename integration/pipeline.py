import cv2
import numpy as np
import os
import sys
import tensorflow as tf

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from cv.pipeline_cv import apply_clahe, apply_grabcut, check_quality

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

# ─── 1. CAPTURE ───────────────────────────────────────────────
def capture_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image introuvable : {image_path}")
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

# ─── 3. INFÉRENCE (vrai modèle TFLite de A) ───────────────────
def inference(image):
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
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

# ─── 4. PIPELINE COMPLET ──────────────────────────────────────
def run_pipeline(image_path):
    image = capture_image(image_path)
    image_preprocessed = preprocess(image)
    resultats = inference(image_preprocessed)
    return resultats

if __name__ == "__main__":
    resultats = run_pipeline("data/test_feuille.jpg")
    print("\n=== RÉSULTATS ===")
    for r in resultats:
        print(f"{r['maladie']} : {r['confiance']*100:.1f}%")