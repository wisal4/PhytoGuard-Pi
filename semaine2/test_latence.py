import numpy as np
import time
from ai_edge_litert.interpreter import Interpreter

MODEL_PATH = "/home/pi/phytoguard/phytoguard_int8.tflite"

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

print("Chargement du modèle...")
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print(f"✅ Modèle chargé")
print(f"   Input shape : {input_details[0]['shape']}")

# Test de latence sur 20 inférences
print("\nMesure de latence (20 inférences)...")
latences = []

for i in range(20):
    img = np.random.randint(0, 255, (1, 224, 224, 3), dtype=np.float32)
    start = time.perf_counter()
    interpreter.set_tensor(input_details[0]['index'], img)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    end = time.perf_counter()
    latences.append((end - start) * 1000)
    print(f"  Inférence {i+1:02d} : {latences[-1]:.1f} ms")

print(f"\n📊 Résultats :")
print(f"   Latence moyenne : {np.mean(latences):.1f} ms")
print(f"   Latence min     : {np.min(latences):.1f} ms")
print(f"   Latence max     : {np.max(latences):.1f} ms")

# Test top-3 sur une image aléatoire
print(f"\n🔍 Test top-3 :")
img = np.random.randint(0, 255, (1, 224, 224, 3), dtype=np.float32)
interpreter.set_tensor(input_details[0]['index'], img)
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])[0]
top3 = np.argsort(output)[-3:][::-1]
for rank, idx in enumerate(top3):
    print(f"   {rank+1}. {CLASS_NAMES[idx]} — {output[idx]*100:.1f}%")

print("\n✅ Test terminé !")
