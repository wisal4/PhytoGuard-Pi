import time
import numpy as np
from ai_edge_litert.interpreter import Interpreter

model = Interpreter(model_path="unet_lesions.tflite")
model.allocate_tensors()
input_details = model.get_input_details()
output_details = model.get_output_details()

latencies = []
for _ in range(20):
    dummy = np.random.rand(1, 256, 256, 3).astype(np.float32)
    start = time.perf_counter()
    model.set_tensor(input_details[0]['index'], dummy)
    model.invoke()
    _ = model.get_tensor(output_details[0]['index'])
    end = time.perf_counter()
    latencies.append((end - start)*1000)

print(f"U‑Net INT8 : {np.mean(latencies):.1f} ± {np.std(latencies):.1f} ms")