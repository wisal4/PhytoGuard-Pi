import cv2
import numpy as np
import os
from skimage.feature import local_binary_pattern

# ─── 1. CHARGER UNE IMAGE ───────────────────────────────
def load_image(path):
    img = cv2.imread(path)
    if img is None:
        print(f"Erreur : impossible de charger {path}")
        return None
    print(f"✅ Image chargée : {img.shape}")
    return img

# ─── 2. CLAHE (correction luminosité) ───────────────────
def apply_clahe(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l_clahe = clahe.apply(l)
    lab_clahe = cv2.merge((l_clahe, a, b))
    result = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
    print("✅ CLAHE appliqué")
    return result

# ─── 3. GRABCUT (segmentation feuille) ──────────────────
def apply_grabcut(img):
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    h, w = img.shape[:2]
    rect = (10, 10, w-10, h-10)
    cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5,
                cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
    result = img * mask2[:,:,np.newaxis]
    print("✅ GrabCut appliqué")
    return result, mask2

# ─── 4. QUALITÉ IMAGE ───────────────────────────────────
def check_quality(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    print(f"📊 Score netteté : {score:.2f}")
    if score < 100:
        print("⚠️  Image floue !")
        return False, score
    print("✅ Image nette")
    return True, score

# ─── 5. FEATURES HSV ────────────────────────────────────
def extract_hsv_features(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    features = []
    for i in range(3):
        features.append(hsv[:,:,i].mean())
        features.append(hsv[:,:,i].std())
    print(f"✅ Features HSV : {np.round(features, 2)}")
    return np.array(features)

# ─── 6. FEATURES LBP ────────────────────────────────────
def extract_lbp_features(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lbp = local_binary_pattern(gray, P=8, R=1, method='uniform')
    hist, _ = np.histogram(lbp.ravel(), bins=10, range=(0,10))
    hist = hist / hist.sum()
    print(f"✅ Features LBP : {np.round(hist, 3)}")
    return hist

# ─── 7. SAUVEGARDER IMAGE TRAITÉE ───────────────────────
def save_processed_image(img_original, img_clahe, img_grabcut, 
                          mask, image_name, output_dir="../output/processed"):
    """
    Sauvegarde 3 images :
    1. Image originale
    2. Image après CLAHE
    3. Image après GrabCut (feuille isolée)
    + Image comparaison côte à côte
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(image_name)[0]

    # Sauvegarder les 3 images
    path_original = os.path.join(output_dir, f"{base_name}_original.jpg")
    path_clahe    = os.path.join(output_dir, f"{base_name}_clahe.jpg")
    path_grabcut  = os.path.join(output_dir, f"{base_name}_grabcut.jpg")

    cv2.imwrite(path_original, img_original)
    cv2.imwrite(path_clahe, img_clahe)
    cv2.imwrite(path_grabcut, img_grabcut)

    # Image comparaison côte à côte
    h, w = img_original.shape[:2]
    comparison = np.zeros((h, w*3, 3), dtype=np.uint8)
    comparison[:, :w]      = img_original
    comparison[:, w:w*2]   = img_clahe
    comparison[:, w*2:w*3] = img_grabcut

    # Ajouter labels
    cv2.putText(comparison, "ORIGINAL", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
    cv2.putText(comparison, "CLAHE", (w+10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
    cv2.putText(comparison, "GRABCUT", (w*2+10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    path_comparison = os.path.join(output_dir, f"{base_name}_comparison.jpg")
    cv2.imwrite(path_comparison, comparison)

    print(f"💾 Images sauvegardées dans : {output_dir}")
    print(f"   → {base_name}_original.jpg")
    print(f"   → {base_name}_clahe.jpg")
    print(f"   → {base_name}_grabcut.jpg")
    print(f"   → {base_name}_comparison.jpg")

    return path_grabcut  # Retourne l'image traitée pour Membre A

# ─── PIPELINE COMPLET ────────────────────────────────────
def run_pipeline(image_path):
    print(f"\n{'='*50}")
    print(f"🌿 Analyse : {os.path.basename(image_path)}")
    print(f"{'='*50}")

    # Charger
    img = load_image(image_path)
    if img is None:
        return None

    # Vérifier qualité
    nette, score = check_quality(img)
    if not nette:
        print("⚠️  Image rejetée — qualité insuffisante")

    # Traitement
    img_clahe = apply_clahe(img)
    img_grabcut, mask = apply_grabcut(img_clahe)

    # Extraire features
    hsv_features = extract_hsv_features(img_grabcut)
    lbp_features = extract_lbp_features(img_grabcut)

    # ── NOUVEAU : Sauvegarder l'image traitée ──────────
    image_name = os.path.basename(image_path)
    path_traitee = save_processed_image(
        img, img_clahe, img_grabcut, mask, image_name
    )

    print(f"\n✅ Pipeline terminé !")
    print(f"   HSV features : {len(hsv_features)} valeurs")
    print(f"   LBP features : {len(lbp_features)} valeurs")
    print(f"   Image traitée : {path_traitee}")
    print(f"   → Prête pour Membre A (EfficientNet) ✅")

    return {
        'hsv_features': hsv_features,
        'lbp_features': lbp_features,
        'image_traitee': path_traitee,
        'nettete': score,
        'img_grabcut': img_grabcut
    }

# ─── TEST SUR 5 IMAGES ───────────────────────────────────
if __name__ == "__main__":
    base = "../data/images/PlantVillage/"
    categories = os.listdir(base)
    count = 0

    for cat in categories[:5]:
        cat_path = os.path.join(base, cat)
        images = os.listdir(cat_path)
        if images:
            img_path = os.path.join(cat_path, images[0])
            result = run_pipeline(img_path)
            if result:
                count += 1

    print(f"\n🎉 {count} images traitées et sauvegardées !")
    print(f"📁 Voir les images dans : ../output/processed/")
