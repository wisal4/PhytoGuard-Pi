import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from pipeline import run_pipeline

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

images = [f for f in os.listdir(data_dir) 
          if f.endswith(".jpg") or f.endswith(".png")]

print(f"=== TEST SUR {len(images)} IMAGES ===\n")

for i, img_name in enumerate(images):
    img_path = os.path.join(data_dir, img_name)
    print(f"--- Image {i+1} : {img_name} ---")
    try:
        resultats = run_pipeline(img_path)
        print(f"✅ Résultat : {resultats[0]['maladie']} ({resultats[0]['confiance']*100:.1f}%)")
    except Exception as e:
        print(f"❌ Erreur : {e}")
    print()

print("=== TESTS TERMINÉS ===")