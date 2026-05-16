import tensorflow as tf
import numpy as np
import os

MODEL_PATH = "best_final.keras"
OUTPUT_PATH = "phytoguard_int8.tflite"
DATA_DIR = "plantvillage-dataset/plantvillage_dataset/color"

print("Chargement du modèle...")
model = tf.keras.models.load_model(MODEL_PATH)
print("✅ Modèle chargé")

# Dataset de calibration (nécessaire pour INT8)
# On prend 100 images aléatoires pour calibrer la quantification
from tensorflow.keras.preprocessing.image import ImageDataGenerator

gen = ImageDataGenerator()
calib_gen = gen.flow_from_directory(
    DATA_DIR,
    target_size=(224, 224),
    batch_size=1,
    class_mode=None,
    shuffle=True
)

def representative_dataset():
    for i, batch in enumerate(calib_gen):
        if i >= 100:
            break
        yield [batch.astype(np.float32)]

# Conversion INT8
print("\nConversion en TFLite INT8...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.float32
converter.inference_output_type = tf.float32

tflite_model = converter.convert()

with open(OUTPUT_PATH, 'wb') as f:
    f.write(tflite_model)

size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
print(f"\n✅ Modèle TFLite INT8 sauvegardé : {OUTPUT_PATH}")
print(f"   Taille originale (.keras) : {os.path.getsize(MODEL_PATH)/1024/1024:.1f} MB")
print(f"   Taille TFLite INT8        : {size_mb:.1f} MB")
print(f"   Réduction                 : {(1 - size_mb/(os.path.getsize(MODEL_PATH)/1024/1024))*100:.0f}%")