import numpy as np
import cv2
from ai_edge_litert.interpreter import Interpreter

class TTAUnet:
    def __init__(self, model_path):
        self.interpreter = Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
    
    def predict(self, image):
        """
        Prédiction avec TTA (rotations 0°, 90°, 180°, 270°)
        image: numpy array (256, 256, 3) en float32
        retourne: masque segmenté (256, 256) en float32
        """
        predictions = []
        
        # Original (0°)
        pred0 = self._predict_single(image)
        predictions.append(pred0)
        
        # Rotation 90°
        rot90 = np.rot90(image, k=1, axes=(0,1))
        pred90 = self._predict_single(rot90)
        pred90 = np.rot90(pred90, k=-1, axes=(0,1))
        predictions.append(pred90)
        
        # Rotation 180°
        rot180 = np.rot90(image, k=2, axes=(0,1))
        pred180 = self._predict_single(rot180)
        pred180 = np.rot90(pred180, k=-2, axes=(0,1))
        predictions.append(pred180)
        
        # Rotation 270°
        rot270 = np.rot90(image, k=3, axes=(0,1))
        pred270 = self._predict_single(rot270)
        pred270 = np.rot90(pred270, k=-3, axes=(0,1))
        predictions.append(pred270)
        
        # Moyenne des 4 prédictions
        return np.mean(predictions, axis=0)
    
    def _predict_single(self, image):
        input_tensor = image.reshape(1, 256, 256, 3).astype(np.float32)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_tensor)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        return output[0, :, :, 0]

# Test rapide
if __name__ == "__main__":
    print("Test TTA U-Net...")
    tta = TTAUnet("unet_lesions.tflite")
    dummy = np.random.rand(256, 256, 3).astype(np.float32)
    mask = tta.predict(dummy)
    print(f"✅ Masque généré : forme {mask.shape}, valeur moyenne {mask.mean():.3f}")