import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Render'dan anahtarı çekiyoruz
API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    try:
        # Kapı 1: v1 sürümü üzerinden Gemini 1.5 Flash dene
        gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        
        payload = {
            "contents": [{"parts": [{"text": "Yorumları 3 cümlede özetle: Ürün harika, kargo hızlı."}]}]
        }
        
        response = requests.post(gemini_url, json=payload, timeout=10)
        res_data = response.json()

        if "candidates" in res_data:
            return jsonify({"sonuc": res_data['candidates'][0]['content']['parts'][0]['text']})
        
        # Eğer yukarıdaki hata verirse, Kapı 2: Gemini Pro dene
        return jsonify({"hata": "Model uyuşmazlığı", "detay": res_data}), 500

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
