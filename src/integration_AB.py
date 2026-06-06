import cv2
import numpy as np
import os
import time

# ─── CHEMINS DES MODÈLES ────────────────────────────────
MODEL_EFFICIENTNET = "../models/phytoguard_int8.tflite"
MODEL_UNET = "../models/unet_lesions.tflite"

# 38 Classes PlantVillage
CLASSES = [
    'Apple_Apple_scab', 'Apple_Black_rot', 'Apple_Cedar_apple_rust', 'Apple_healthy',
    'Blueberry_healthy', 'Cherry_Powdery_mildew', 'Cherry_healthy',
    'Corn_Cercospora_leaf_spot', 'Corn_Common_rust', 'Corn_Northern_Leaf_Blight', 'Corn_healthy',
    'Grape_Black_rot', 'Grape_Esca', 'Grape_Leaf_blight', 'Grape_healthy',
    'Orange_Haunglongbing', 'Peach_Bacterial_spot', 'Peach_healthy',
    'Pepper_bell_Bacterial_spot', 'Pepper_bell_healthy',
    'Potato_Early_blight', 'Potato_Late_blight', 'Potato_healthy',
    'Raspberry_healthy', 'Soybean_healthy', 'Squash_Powdery_mildew',
    'Strawberry_Leaf_scorch', 'Strawberry_healthy',
    'Tomato_Bacterial_spot', 'Tomato_Early_blight', 'Tomato_Late_blight',
    'Tomato_Leaf_Mold', 'Tomato_Septoria_leaf_spot',
    'Tomato_Spider_mites', 'Tomato_Target_Spot',
    'Tomato_YellowLeaf_Curl_Virus', 'Tomato_mosaic_virus', 'Tomato_healthy'
]

# ─── CHARGER MODÈLE TFLITE ──────────────────────────────
def load_model(path):
    try:
        from ai_edge_litert.interpreter import Interpreter
        interp = Interpreter(model_path=path)
    except ImportError:
        try:
            import tflite_runtime.interpreter as tflite
            interp = tflite.Interpreter(model_path=path)
        except ImportError:
            import tensorflow as tf
            interp = tf.lite.Interpreter(model_path=path)
    interp.allocate_tensors()
    print(f"✅ Modèle chargé : {os.path.basename(path)}")
    return interp

# ─── MEMBRE B : PIPELINE CV ─────────────────────────────
def pipeline_cv(img):
    print("\n🔧 [Membre B] Pipeline CV...")

    # CLAHE
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l_clahe = clahe.apply(l)
    img_clahe = cv2.cvtColor(cv2.merge((l_clahe, a, b)), cv2.COLOR_LAB2BGR)
    print("   ✅ CLAHE appliqué")

    # GrabCut
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd = np.zeros((1,65), np.float64)
    fgd = np.zeros((1,65), np.float64)
    h, w = img.shape[:2]
    cv2.grabCut(img_clahe, mask, (10,10,w-10,h-10), bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
    img_masked = img_clahe * mask2[:,:,np.newaxis]
    print("   ✅ GrabCut appliqué")

    # Qualité
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    nettete = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Features HSV
    hsv = cv2.cvtColor(img_masked, cv2.COLOR_BGR2HSV)
    hsv_features = []
    for i in range(3):
        hsv_features.extend([hsv[:,:,i].mean(), hsv[:,:,i].std()])
    hsv_features = np.array(hsv_features)

    # Verdure
    mask_vert = cv2.inRange(hsv, np.array([35,40,40]), np.array([85,255,255]))
    verdure = (np.sum(mask_vert>0) / (h*w)) * 100

    print(f"   📊 Netteté: {nettete:.2f} | Verdure: {verdure:.1f}%")
    print(f"   ✅ Features HSV: {np.round(hsv_features, 2)}")

    return img_masked, hsv_features, nettete, verdure

# ─── MEMBRE A : CLASSIFICATION EFFICIENTNET ─────────────
def classification_efficientnet(interp, img):
    print("\n🤖 [Membre A] Classification EfficientNet...")
    t_start = time.time()

    input_details = interp.get_input_details()
    output_details = interp.get_output_details()

    # Prétraitement avec numpy view
    img_resized = cv2.resize(img, (224, 224))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_float = img_rgb.astype(np.float32) / 255.0
    input_tensor = img_float[np.newaxis, :]

    if input_details[0]['dtype'] == np.uint8:
        input_tensor = (input_tensor * 255).astype(np.uint8)

    interp.set_tensor(input_details[0]['index'], input_tensor)
    interp.invoke()

    output = interp.get_tensor(output_details[0]['index'])[0].astype(np.float32)
    if output_details[0]['dtype'] == np.uint8:
        scale, zp = output_details[0]['quantization']
        output = (output - zp) * scale

    scores = np.exp(output) / np.sum(np.exp(output))
    top3_idx = np.argsort(scores)[::-1][:3]

    latence = (time.time() - t_start) * 1000
    print(f"   ⏱️  Latence: {latence:.2f}ms")
    print(f"   🏆 Top 3 prédictions:")
    for i, idx in enumerate(top3_idx):
        classe = CLASSES[idx] if idx < len(CLASSES) else f"Classe_{idx}"
        print(f"      {i+1}. {classe} ({scores[idx]*100:.1f}%)")

    top_idx = top3_idx[0]
    top_classe = CLASSES[top_idx] if top_idx < len(CLASSES) else f"Classe_{top_idx}"
    top_conf = float(scores[top_idx])

    return top_classe, top_conf, latence, top3_idx, scores

# ─── MEMBRE A : SEGMENTATION U-NET ──────────────────────
def segmentation_unet(interp, img):
    print("\n🔬 [Membre A] Segmentation U-Net...")
    t_start = time.time()

    input_details = interp.get_input_details()
    output_details = interp.get_output_details()

    # Prétraitement U-Net (256x256)
    input_shape = input_details[0]['shape']
    h_in = input_shape[1]
    w_in = input_shape[2]

    img_resized = cv2.resize(img, (w_in, h_in))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_float = img_rgb.astype(np.float32) / 255.0
    input_tensor = img_float[np.newaxis, :]

    if input_details[0]['dtype'] == np.uint8:
        input_tensor = (input_tensor * 255).astype(np.uint8)

    interp.set_tensor(input_details[0]['index'], input_tensor)
    interp.invoke()

    output = interp.get_tensor(output_details[0]['index'])[0]

    # Calculer % surface lésions
    if len(output.shape) == 3:
        mask_lesion = output[:,:,0] > 0.5
    else:
        mask_lesion = output > 0.5

    surface_lesion = (np.sum(mask_lesion) / mask_lesion.size) * 100
    latence = (time.time() - t_start) * 1000

    print(f"   ⏱️  Latence: {latence:.2f}ms")
    print(f"   🔴 Surface lésions: {surface_lesion:.1f}%")

    # Niveau de sévérité BBCH
    if surface_lesion < 5:
        severite = 0
        niveau = "Sain"
    elif surface_lesion < 15:
        severite = 1
        niveau = "Léger"
    elif surface_lesion < 30:
        severite = 2
        niveau = "Modéré"
    elif surface_lesion < 50:
        severite = 3
        niveau = "Sévère"
    else:
        severite = 4
        niveau = "Critique"

    print(f"   📊 Sévérité BBCH: {severite}/4 ({niveau})")

    return surface_lesion, severite, niveau, latence

# ─── PIPELINE INTÉGRÉ A+B ────────────────────────────────
def run_integration(image_path):
    print(f"\n{'='*55}")
    print(f"🌿 DIAGNOSTIC PHYTOGUARD — {os.path.basename(image_path)}")
    print(f"{'='*55}")

    # Charger image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Image non trouvée : {image_path}")
        return

    t_total = time.time()

    # ── Membre B : Pipeline CV ──────────────────────────
    img_processed, hsv_features, nettete, verdure = pipeline_cv(img)

    # ── Membre A : Classification ───────────────────────
    classe, confiance, lat_classif, top3, scores = classification_efficientnet(
        interp_efficientnet, img_processed)

    # ── Membre A : Segmentation ─────────────────────────
    surface, severite, niveau, lat_unet = segmentation_unet(
        interp_unet, img_processed)

    latence_totale = (time.time() - t_total) * 1000

    # ── Résultat final ──────────────────────────────────
    print(f"""
╔═══════════════════════════════════════════════╗
║           RÉSULTAT DIAGNOSTIC                 ║
╠═══════════════════════════════════════════════╣
║  🌿 Maladie détectée : {classe[:30]:<30} ║
║  📊 Confiance        : {confiance*100:>5.1f}%                     ║
║  🔴 Surface lésions  : {surface:>5.1f}%                     ║
║  ⚠️  Sévérité BBCH   : {severite}/4 ({niveau:<8})            ║
║  📷 Netteté image    : {nettete:>8.2f}                  ║
║  🌱 Verdure          : {verdure:>5.1f}%                     ║
║  ⏱️  Temps total      : {latence_totale:>6.1f}ms                   ║
╚═══════════════════════════════════════════════╝
    """)

    return {
        'maladie': classe,
        'confiance': confiance,
        'surface_lesions': surface,
        'severite': severite,
        'niveau': niveau,
        'latence_ms': latence_totale
    }

# ─── TEST SUR 5 IMAGES ──────────────────────────────────
if __name__ == "__main__":
    print("\n🚀 INTÉGRATION MEMBRE A + MEMBRE B")
    print("="*55)

    # Charger les modèles
    print("\n📦 Chargement des modèles...")
    interp_efficientnet = load_model(MODEL_EFFICIENTNET)
    interp_unet = load_model(MODEL_UNET)

    # Tester sur 5 images
    base = "../data/images/PlantVillage/"
    categories = os.listdir(base)
    total = 0

    for cat in categories:
        if total >= 5:
            break
        cat_path = os.path.join(base, cat)
        images = os.listdir(cat_path)
        if images:
            img_path = os.path.join(cat_path, images[0])
            run_integration(img_path)
            total += 1

    print(f"\n🎉 Intégration A+B testée sur {total} images avec succès !")
