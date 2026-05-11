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

    product_name = url.split('/')[-1].replace('-', ' ').split('?')[0]
    
    # Platform tespiti
    platform = "Trendyol"
    if "hepsiburada" in url: platform = "Hepsiburada"
    elif "pazarama" in url: platform = "Pazarama"
    elif "idefix" in url: platform = "Idefix"

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": f"""Sen NetPuan AI analizörüsün. 
                    Ürünü ve linkteki platformu ({platform}) analiz et.
                    Verdiğin 'olumlu', 'kargo' ve 'olumsuz' yüzdelerinin TOPLAMI tam olarak %100 olmalıdır.
                    Örnek: olumlu: 70, kargo: 20, olumsuz: 10.
                    JSON formatı: {{'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'platform': '{platform}'}}"""
                },
                {"role": "user", "content": f"Ürün: {product_name}\nPlatform: {platform}\nLink: {url}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post(groq_url, json=payload, headers=headers)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run()
