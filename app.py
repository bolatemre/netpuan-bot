import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def get_trendyol_comments(url):
    try:
        # Ürün ID'sini çek
        product_id_match = re.search(r"p-(\d+)", url)
        if not product_id_match: return None
        p_id = product_id_match.group(1)

        # DAHA BASİT VE ENGELLEMESİ ZOR BİR API YOLU
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialview-service/api/reviews/{p_id}?storefrontId=1&culture=tr-TR&order=5&showOnlyConfirmedReviews=true&page=0"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
            "Accept": "application/json",
            "Referer": "https://www.trendyol.com/"
        }

        # cloudscraper yerine en sade requests ile "iPhone" gibi davranıyoruz
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            comments = [r['comment'] for r in data.get('content', []) if 'comment' in r]
            return " | ".join(comments[:15])
        return None
    except:
        return None

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    raw_data = get_trendyol_comments(url)
    
    # Veri gelmezse AI'ya "Sallama, hata olduğunu söyle" talimatı
    system_msg = "Sen bir e-ticaret analizörüsün. Eğer veri 'YOK' gelmişse, özete 'Trendyol bot koruması nedeniyle yorumlar şu an çekilemedi. Lütfen sayfayı yenileyip tekrar deneyin.' yaz. Eğer veri varsa dürüstçe analiz et. SADECE JSON formatında cevap ver."
    
    user_msg = f"Analiz edilecek yorumlar: {raw_data if raw_data else 'YOK'}"

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post(groq_url, json=payload, headers=headers)
        result = json.loads(res.json()['choices'][0]['message']['content'])
        return jsonify(result)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run()
