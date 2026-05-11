import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    # 1. Ürün İsmini Linkten Tertemiz Ayıkla
    # Örn: .../philips-airfryer-p-123 -> Philips Airfryer
    product_raw = url.split('/')[-1].split('?')[0]
    product_parts = [w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]
    product_name = ' '.join(product_parts).title()
    
    # 2. Platform Tespiti
    platform = "Trendyol"
    if "hepsiburada" in url: platform = "Hepsiburada"
    elif "pazarama" in url: platform = "Pazarama"
    elif "idefix" in url: platform = "Idefix"
    elif "idefix" in url: platform = "N11"

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": f"""Sen NetPuan AI analizörüsün. 
                    Sana verilen ürün adını ve platformu ({platform}) internetteki geniş kullanıcı deneyimi verilerine dayanarak analiz et.
                    Verdiğin 'olumlu', 'kargo' ve 'olumsuz' yüzdelerinin TOPLAMI tam olarak %100 olmalıdır.
                    Puanı 10 üzerinden dürüstçe ver (Örn: 8.4).
                    JSON formatı: {{"ozet": "...", "puan": 0.0, "olumlu": 0, "kargo": 0, "olumsuz": 0, "platform": "{platform}", "urun_adi": "{product_name}"}}"""
                },
                {"role": "user", "content": f"Ürün: {product_name}\nPlatform: {platform}\nLink: {url}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post(groq_url, json=payload, headers=headers, timeout=15)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run()
