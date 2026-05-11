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
    query = request.args.get('url') # Artık hem URL hem de İsim gelebilir
    if not query: return jsonify({"hata": "Arama terimi veya link eksik"}), 400

    # 1. Girişin Link mi yoksa Ürün İsmi mi olduğunu anla
    if query.startswith("http"):
        # Linkten Ürün İsmi Çıkarma
        url = query
        product_raw = url.split('/')[-1].split('?')[0]
        product_parts = [w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]
        product_name = ' '.join(product_parts).title()
        
        # Platform Tespiti
        platform = "Trendyol"
        if "hepsiburada" in url: platform = "Hepsiburada"
        elif "pazarama" in url: platform = "Pazarama"
        elif "idefix" in url: platform = "Idefix"
        elif "n11.com" in url: platform = "N11"
    else:
        # Doğrudan isim girilmiş
        url = "Manuel Arama"
        product_name = query.title()
        platform = "Genel Pazaryeri"

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": f"""Sen NetPuan AI analizörüsün. 
                    Sana verilen ürün adını ({product_name}) ve varsa platformu ({platform}) internetteki geniş kullanıcı deneyimi, kronik sorunlar ve genel müşteri memnuniyeti verilerine dayanarak analiz et.
                    
                    KURALLAR:
                    1. 'olumlu', 'kargo' ve 'olumsuz' yüzdelerinin TOPLAMI tam olarak %100 olmalıdır.
                    2. Puanı 10 üzerinden dürüstçe ver (Örn: 7.2).
                    3. Eğer ürün çok bilindik bir ürünse (iPhone, Dyson vb.) kronik şikayetleri 'ozet' kısmında belirt.
                    
                    JSON formatı: {{"ozet": "...", "puan": 0.0, "olumlu": 0, "kargo": 0, "olumsuz": 0, "platform": "{platform}", "urun_adi": "{product_name}"}}"""
                },
                {"role": "user", "content": f"Ürün: {product_name}\nPlatform: {platform}\nKaynak: {url}"}
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
