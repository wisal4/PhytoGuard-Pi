import tensorflow as tf
import os

# Charge le modèle sans compiler (ignore les fonctions custom)
print("Chargement du modèle sans compilation...")
model = tf.keras.models.load_model("unet_best.keras", compile=False)
print("✅ Modèle chargé")

# Recompile avec une loss standard (on s'en fiche, on veut juste convertir)
model.compile(optimizer='adam', loss='binary_crossentropy')

print("Conversion en TFLite FP16...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.float16]

tflite_fp16 = converter.convert()

with open("unet_fp16.tflite", "wb") as f:
    f.write(tflite_fp16)

size_mb = os.path.getsize("unet_fp16.tflite") / 1024 / 1024
print(f"✅ Fichier sauvegardé : unet_fp16.tflite ({size_mb:.1f} MB)")