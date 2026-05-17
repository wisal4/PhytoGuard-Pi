from flask import Flask, render_template_string, request
from pipeline import run_pipeline
import os

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PhytoGuard-Pi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: Arial;
            background: #f5f5f5;
            padding: 15px;
            min-height: 100vh;
        }
        h1 {
            color: #2d6a2d;
            font-size: 28px;
            text-align: center;
            padding: 15px 0;
            border-bottom: 3px solid #2d6a2d;
            margin-bottom: 20px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            font-size: 16px;
            margin-bottom: 20px;
        }
        .upload-zone {
            background: white;
            border: 3px dashed #2d6a2d;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            margin-bottom: 20px;
        }
        input[type="file"] {
            font-size: 18px;
            padding: 10px;
            width: 100%;
            margin-bottom: 20px;
        }
        button {
            background: #2d6a2d;
            color: white;
            padding: 20px;
            border: none;
            border-radius: 15px;
            font-size: 22px;
            width: 100%;
            cursor: pointer;
            font-weight: bold;
            letter-spacing: 1px;
        }
        button:active {
            background: #1a4a1a;
            transform: scale(0.98);
        }
        .result {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            border: 2px solid #2d6a2d;
        }
        .result h2 {
            color: #2d6a2d;
            font-size: 22px;
            margin-bottom: 15px;
            text-align: center;
        }
        .result-item {
            background: #f0f7f0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
        }
        .maladie {
            font-size: 20px;
            font-weight: bold;
            color: #c0392b;
            margin-bottom: 5px;
        }
        .culture {
            font-size: 16px;
            color: #2d6a2d;
            margin-bottom: 5px;
        }
        .confiance {
            font-size: 18px;
            color: #333;
        }
        .barre {
            height: 12px;
            background: #ddd;
            border-radius: 6px;
            margin-top: 8px;
            overflow: hidden;
        }
        .barre-fill {
            height: 100%;
            background: #2d6a2d;
            border-radius: 6px;
        }
        .top1 {
            border: 3px solid #c0392b;
        }
    </style>
</head>
<body>
    <h1>🌿 PhytoGuard-Pi</h1>
    <p class="subtitle">Diagnostic de maladies des plantes</p>

    <div class="upload-zone">
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="image" accept="image/*">
            <button type="submit">🔍 ANALYSER</button>
        </form>
    </div>

    {% if resultats %}
    <div class="result">
        <h2>📊 Résultats</h2>
        {% for r in resultats %}
        <div class="result-item {% if loop.first %}top1{% endif %}">
            <p class="culture">{{ r.maladie.split('___')[0] if '___' in r.maladie else '' }}</p>
            <p class="maladie">{{ r.maladie.split('___')[1] if '___' in r.maladie else r.maladie }}</p>
            <p class="confiance">Confiance : {{ "%.1f"|format(r.confiance * 100) }}%</p>
            <div class="barre">
                <div class="barre-fill" style="width: {{ "%.0f"|format(r.confiance * 100) }}%"></div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    resultats = None
    if request.method == "POST":
        image = request.files.get("image")
        if image:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "temp_upload.jpg")
            image.save(path)
            resultats = run_pipeline(path)
    return render_template_string(HTML, resultats=resultats)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)