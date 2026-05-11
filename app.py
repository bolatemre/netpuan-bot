import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Render Environment'dan anahtarı çekiyoruz
API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    try:
        # Trendyol/Pazaryeri verisi (Şimdilik test metni, API çalışınca burayı açarız)
        comments = "Ürün çok kaliteli, kargo hızlı geldi, tavsiye ederim."

        # DOĞRUDAN GOOGLE API ADRESİ (Kütüphane kullanmıyoruz!)
        # v1 sürümü üzerinden en garantili model
        gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [{"text": f"Şu ürün yorumlarını 3 kısa cümlede analiz et: {comments}"}]
            }]
        }
        
        # Google'a doğrudan POST isteği atıyoruz
        response = requests.post(gemini_url, json=payload, timeout=15)
        res_json = response.json()

        # Yanıtı kontrol et
        if "candidates" in res_json:
            ai_text = res_json['candidates'][0]['content']['parts'][0]['text']
            return jsonify({"sonuc": ai_text})
        else:
            # Hata varsa ne olduğunu açıkça yazdır
            return jsonify({
                "hata": "Google API Hatası",
                "detay": res_json.get('error', {}).get('message', 'Bilinmeyen hata')
            }), 500

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
