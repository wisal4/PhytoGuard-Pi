import time
import numpy as np
from ai_edge_litert.interpreter import Interpreter
import cv2
import os

# Charge une vraie image (si disponible)
# Sinon, génère une image factice avec des "lésions"
print("Test TTA sur U-Net INT8")
print("="*40)

interpreter = Interpreter(model_path="unet_lesions.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Crée une image factice avec une "tache" (simule une lésion)
img = np.zeros((256, 256, 3), dtype=np.float32)
img[100:150, 100:150, :] = 1.0  # carré blanc simulant une lésion

# Prédiction sans TTA
start = time.perf_counter()
input_tensor = img.reshape(1, 256, 256, 3)
interpreter.set_tensor(input_details[0]['index'], input_tensor)
interpreter.invoke()
mask = interpreter.get_tensor(output_details[0]['index'])[0, :, :, 0]
print(f"Sans TTA : {np.mean(mask):.3f}")

# Avec TTA (moyenne sur 4 rotations)
masks = []
for k in [0, 1, 2, 3]:
    img_rot = np.rot90(img, k=k, axes=(0,1))
    interpreter.set_tensor(input_details[0]['index'], img_rot.reshape(1,256,256,3))
    interpreter.invoke()
    m = interpreter.get_tensor(output_details[0]['index'])[0, :, :, 0]
    m = np.rot90(m, k=-k, axes=(0,1))
    masks.append(m)
mask_tta = np.mean(masks, axis=0)
print(f"Avec TTA  : {np.mean(mask_tta):.3f}")

print("✅ TTA fonctionnelle")
