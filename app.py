import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = "AIzaSyCbpHHpgxl3gIOPAAYVdk1g13gwcfre03Y"

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    try:
        comments = "Ürün genel olarak çok kaliteli, kargosu hızlı ve paketlemesi özenliydi."

        # BURASI DEĞİŞTİ: v1beta yerine v1 yazıyoruz
        gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        
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
            # Hata devam ederse model adını v1 altında tekrar kontrol etmek için detay veriyoruz
            return jsonify({"hata": "Google API Hatası", "detay": res_json}), 500

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
