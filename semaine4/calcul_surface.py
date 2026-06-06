import numpy as np
from ai_edge_litert.interpreter import Interpreter
import cv2

def calcul_pourcentage_lesions(mask, seuil=0.5):
    """
    Calcule le pourcentage de surface foliaire atteinte
    mask: sortie du U-Net (valeurs entre 0 et 1)
    seuil: à partir de quelle valeur on considère que c'est une lésion
    """
    mask_binaire = (mask > seuil).astype(np.uint8)
    pct = (mask_binaire.sum() / mask_binaire.size) * 100
    return pct

def analyse_feuille(image_path, model_path="unet_lesions.tflite"):
    """
    Pipeline complet: charge image, prédit, calcule %
    """
    # Chargement
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (256, 256))
    img = img.astype(np.float32) / 255.0
    
    # Prédiction simple (sans TTA pour rapidité)
    interpreter = Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    input_tensor = img.reshape(1, 256, 256, 3).astype(np.float32)
    interpreter.set_tensor(input_details[0]['index'], input_tensor)
    interpreter.invoke()
    mask = interpreter.get_tensor(output_details[0]['index'])[0, :, :, 0]
    
    pct = calcul_pourcentage_lesions(mask)
    return pct, mask

if __name__ == "__main__":
    print("🔬 Outil d'analyse de surface foliaire")
    print("Usage: python calcul_surface.py chemin_image.jpg")