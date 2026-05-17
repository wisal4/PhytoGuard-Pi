import time
import numpy as np
from ai_edge_litert.interpreter import Interpreter
import os

MODEL_DIR = "."

MODELS = {
    "EfficientNet INT8": {
        "file": "phytoguard_int8.tflite",
        "size": 224
    },
    "U-Net INT8": {
        "file": "unet_lesions.tflite",
        "size": 256
    },
    "U-Net FP16": {
        "file": "unet_fp16.tflite",
        "size": 256
    }
}

print("="*50)
print("Benchmark - Semaine 4")
print("="*50)

for name, info in MODELS.items():
    filename = info["file"]
    input_size = info["size"]
    path = os.path.join(MODEL_DIR, filename)
    
    if not os.path.exists(path):
        print(f"\n{filename} non trouve")
        continue
    
    print(f"\n{name} ({input_size}x{input_size})")
    
    interpreter = Interpreter(model_path=path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    
    latencies = []
    for i in range(30):
        dummy = np.random.rand(1, input_size, input_size, 3).astype(np.float32)
        start = time.perf_counter()
        interpreter.set_tensor(input_details[0]['index'], dummy)
        interpreter.invoke()
        end = time.perf_counter()
        latencies.append((end - start) * 1000)
    
    print(f"   Moyenne: {np.mean(latencies):.1f} ms")
    print(f"   Min: {np.min(latencies):.1f} ms")
    print(f"   Max: {np.max(latencies):.1f} ms")