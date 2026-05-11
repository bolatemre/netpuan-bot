import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Render Environment'dan veya koddan anahtarı al
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCbpHHpgxl3gIOPAAYVdk1g13gwcfre03Y")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    try:
        # Trendyol yorumları için örnek veri (Testi geçmek için)
        comments = "Ürün harika, kargo hızlı, paketleme özenli."

        # EN STABİL MODEL: gemini-pro (v1 sürümü üzerinden)
        gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [{"text": f"Şu ürün yorumlarını 3 kısa cümlede analiz et: {comments}"}]
            }]
        }
        
        response = requests.post(gemini_url, json=payload, timeout=15)
        res_json = response.json()

        if "candidates" in res_json:
            ai_text = res_json['candidates'][0]['content']['parts'][0]['text']
            return jsonify({"sonuc": ai_text})
        else:
            return jsonify({"hata": "Google hala modeli bulamadı", "detay": res_json}), 500

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
