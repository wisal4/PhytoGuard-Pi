from flask import Flask, render_template_string, request
from pipeline import run_pipeline
import os

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PhytoGuard-Pi</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
        h1 { color: #2d6a2d; }
        .result { background: #f0f7f0; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .maladie { font-size: 24px; font-weight: bold; color: #c0392b; }
        .confiance { font-size: 18px; color: #2d6a2d; }
        button { background: #2d6a2d; color: white; padding: 12px 30px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>PhytoGuard-Pi</h1>
    <p>Diagnostic de maladies des plantes</p>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="image" accept="image/*" style="margin: 10px 0; display: block;">
        <button type="submit">Analyser</button>
    </form>
    {% if resultats %}
    <div class="result">
        <h2>Résultats :</h2>
        {% for r in resultats %}
        <p class="maladie">{{ r.maladie }}</p>
        <p class="confiance">Confiance : {{ "%.1f"|format(r.confiance * 100) }}%</p>
        <hr>
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