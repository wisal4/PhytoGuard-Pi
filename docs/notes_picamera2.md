# Notes PiCamera2

## C'est quoi
Bibliothèque Python officielle pour contrôler la caméra du Raspberry Pi 5.

## Code de base pour capturer une image
```python
from picamera2 import Picamera2
import cv2

picam = Picamera2()
config = picam.create_still_configuration(
    main={"size": (1920, 1080), "format": "RGB888"}
)
picam.configure(config)
picam.start()
frame = picam.capture_array()
cv2.imwrite("capture.jpg", frame)
picam.stop()
```

## Points importants
- Format image : RGB888 pour OpenCV
- Résolution test : 640x480 (rapide)
- Résolution finale : 1920x1080
- La caméra se branche sur le port CSI du Pi (pas USB)

## Questions à creuser en S2
- Comment gérer la luminosité automatiquement ?
- Quel mode pour les photos en plein soleil ?