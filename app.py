import os
import cloudscraper
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def trendyol_yorum_cek(url):
    try:
        # Linkten ürün ID'sini bul
        match = re.search(r"p-(\d+)", url)
        if not match: return None
        
        product_id = match.group(1)
        # Trendyol Yorum API Adresi
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialview-service/api/reviews/{product_id}?storefrontId=1&culture=tr-TR&order=5&searchValue=&showOnlyConfirmedReviews=true&page=0"
        
        # Cloudscraper ile bot engelini aşıyoruz
        scraper = cloudscraper.create_scraper() 
        res = scraper.get(api_url, timeout=10)
        
        if res.status_code != 200:
            return None
            
        data = res.json()
        comments = [item['comment'] for item in data.get('content', []) if 'comment' in item and item['comment']]
        
        return " | ".join(comments[:20])
    except Exception as e:
        print(f"Hata: {e}")
        return None

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    raw_comments = trendyol_yorum_cek(url)
    
    # AI'ya gidecek mesaj
    if not raw_comments:
        raw_comments = "HATA: Yorumlar çekilemedi. Trendyol erişimi engelledi."

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": "Sen bir analizörsün. Yorumlar gelmişse dürüstçe puanla. Eğer 'HATA' yazıyorsa, özette 'Trendyol şu an veri vermiyor, lütfen 1 dk sonra deneyin' yaz ve tüm puanları 0 yap. SADECE JSON ver."
                },
                {"role": "user", "content": f"Veri: {raw_comments}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        response = scraper.post(groq_url, json=payload, headers=headers_groq) if 'scraper' in locals() else requests.post(groq_url, json=payload, headers=headers_groq)
        result = json.loads(response.json()['choices'][0]['message']['content'])
        return jsonify(result)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
