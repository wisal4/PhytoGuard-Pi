"""
Test de liaison PC - Membre B → Membre A
"""

from inference_v2 import PhytoGuardInference
import cv2
import numpy as np
import os

print("="*50)
print("TEST LIAISON MEMBRE B → MEMBRE A (PC)")
print("="*50)

# 1. Vérifie que les modèles sont présents
fichiers_necessaires = ["phytoguard_int8.tflite", "unet_lesions.tflite"]
for f in fichiers_necessaires:
    if not os.path.exists(f):
        print(f"❌ Fichier manquant : {f}")
        exit(1)
    print(f"✅ {f} trouvé")

# 2. Charge ton modèle
print("\n🔧 Chargement du modèle IA...")
modele_ia = PhytoGuardInference()
print("✅ Modèle chargé")

# 3. Crée une image de test (si B n'a pas de vraie image)
print("\n📷 Création d'une image de test...")
image_test = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
cv2.imwrite("test_fake.jpg", cv2.cvtColor(image_test, cv2.COLOR_RGB2BGR))
print("   Image factice créée : test_fake.jpg")

# 4. Simule le pipeline de B (charge l'image)
image = cv2.imread("test_fake.jpg")
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
print(f"   Taille image : {image.shape}")

# 5. Appelle ton modèle
print("\n🔍 Analyse par IA...")
resultat = modele_ia.predict_from_array(image)

# 6. Affiche les résultats
print("\n" + "="*50)
print("📊 RÉSULTATS")
print("="*50)
print(f"\n🏥 Maladie détectée : {resultat['predicted_disease']}")
print(f"   Confiance : {resultat['top_3'][0]['confiance']:.1f}%")
print(f"\n🌿 Surface lésions : {resultat['lesion_percent']:.1f}%")
print(f"   Sévérité BBCH : {resultat['severity_bbch']}/5")
print(f"\n📋 Top 3 :")
for i, m in enumerate(resultat['top_3']):
    print(f"   {i+1}. {m['classe']} ({m['confiance']:.1f}%)")

print("\n✅ Test PC réussi !")