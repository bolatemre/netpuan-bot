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

    try:
        # Trendyol'un engeline takılmamak için yorumları 
        # Yapay Zeka'nın kendi geniş veritabanından ve linkteki ipuçlarından tahmin etmesini isteyeceğiz.
        # Bu yöntem %100 "Trendyol Engeli" yemez.
        
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        # Linkten ürün adını kabaca çıkaralım
        product_name = url.split('/')[-1].replace('-', ' ').split('?')[0]

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": "Sen dünyanın en zeki e-ticaret uzmanısın. Sana verilen ürün linkini ve ürün adını incele. Bu ürünün Trendyol üzerindeki genel kullanıcı geri bildirimlerini, kronik sorunlarını ve kargo performansını genel internet verilerine dayanarak analiz et. SADECE JSON formatında cevap ver: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0}"
                },
                {"role": "user", "content": f"Ürün Linki: {url}\nÜrün Adı: {product_name}\nLütfen bu ürünü analiz et."}
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
