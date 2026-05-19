"""
Script d'inférence pour liaison avec Membre B
Accepte une image déjà traitée (CLAHE + GrabCut)
"""

import numpy as np
import cv2
from ai_edge_litert.interpreter import Interpreter
import json

class PhytoGuardInference:
    def __init__(self, 
                 model_path_classif="phytoguard_int8.tflite",
                 model_path_seg="unet_lesions.tflite"):
        
        print("🔧 Chargement des modèles...")
        self.classifier = Interpreter(model_path=model_path_classif)
        self.classifier.allocate_tensors()
        self.segmenter = Interpreter(model_path=model_path_seg)
        self.segmenter.allocate_tensors()
        
        self.input_classif = self.classifier.get_input_details()[0]
        self.input_seg = self.segmenter.get_input_details()[0]
        self.output_classif = self.classifier.get_output_details()[0]
        self.output_seg = self.segmenter.get_output_details()[0]
        
        self.class_names = [
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
        print("✅ Modèles chargés")
    
    def predict_from_array(self, image_array):
        """
        Reçoit une image déjà traitée par Membre B
        image_array : numpy array (H, W, 3) en RGB, valeurs 0-255
        """
        # Classification (224x224)
        img_classif = cv2.resize(image_array, (224, 224)).astype(np.float32)
        self.classifier.set_tensor(self.input_classif['index'], 
                                   img_classif.reshape(1, 224, 224, 3))
        self.classifier.invoke()
        output = self.classifier.get_tensor(self.output_classif['index'])[0]
        
        top3_idx = np.argsort(output)[-3:][::-1]
        top3 = [{"classe": self.class_names[i], 
                 "confiance": float(output[i])} for i in top3_idx]
        
        # Segmentation (256x256)
        img_seg = cv2.resize(image_array, (256, 256)).astype(np.float32)
        self.segmenter.set_tensor(self.input_seg['index'], 
                                  img_seg.reshape(1, 256, 256, 3))
        self.segmenter.invoke()
        mask = self.segmenter.get_tensor(self.output_seg['index'])[0, :, :, 0]
        
        lesion_percent = float((mask > 0.5).mean() * 100)
        
        # Sévérité BBCH (1 à 5)
        if lesion_percent < 5:
            severity = 1
        elif lesion_percent < 15:
            severity = 2
        elif lesion_percent < 30:
            severity = 3
        elif lesion_percent < 50:
            severity = 4
        else:
            severity = 5
        
        return {
            "top_3": top3,
            "lesion_percent": round(lesion_percent, 1),
            "severity_bbch": severity,
            "predicted_disease": top3[0]["classe"]
        }
    
    def predict_from_file(self, image_path):
        """Charge une image depuis un fichier"""
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return self.predict_from_array(img)


# Test rapide
if __name__ == "__main__":
    print("Test du pipeline d'inférence")
    model = PhytoGuardInference()
    dummy = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    result = model.predict_from_array(dummy)
    print(json.dumps(result, indent=2))