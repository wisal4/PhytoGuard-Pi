import cv2
import numpy as np
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from cv.pipeline_cv import apply_clahe, apply_grabcut, check_quality

# ─── 1. CAPTURE ───────────────────────────────────────────────
def capture_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image introuvable : {image_path}")
    print(f"[OK] Image chargée : {image.shape}")
    return image

# ─── 2. PRÉTRAITEMENT (pipeline réel de B) ────────────────────
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

# ─── 3. INFÉRENCE (simulée, sera remplacée par A) ─────────────
def inference(image):
    maladies = [
        {"maladie": "Mildiou", "confiance": 0.91},
        {"maladie": "Oïdium",  "confiance": 0.06},
        {"maladie": "Saine",   "confiance": 0.03},
    ]
    print(f"[OK] Inférence simulée : {maladies[0]['maladie']}")
    return maladies

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