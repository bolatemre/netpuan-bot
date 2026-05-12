import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def get_trendyol_comments(p_id):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'referer': 'https://www.trendyol.com/'
        }
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        res = requests.get(api_url, headers=headers, timeout=12)
        if res.status_code == 200:
            return [r['comment'] for r in res.json().get('reviews', []) if 'comment' in r]
        return []
    except:
        return []

def get_hepsiburada_comments(sku):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=40"
        res = requests.get(api_url, headers=headers, timeout=10)
        return [r['review'] for r in res.json().get('data', {}).get('reviews', []) if 'review' in r]
    except:
        return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query:
        return jsonify({"hata": "Link eksik"}), 400

    all_comments = []
    product_name = "Ürün"
    platform = "Genel"

    if "http" in query:
        id_match = re.search(r'p-(\d+)', query)
        if "trendyol.com" in query:
            platform = "Trendyol"
            if id_match:
                all_comments.extend(get_trendyol_comments(id_match.group(1)))
        elif "hepsiburada.com" in query:
            platform = "Hepsiburada"
            sku = query.split('-')[-1].split('?')[0]
            all_comments.extend(get_hepsiburada_comments(sku))
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        comment_text = " | ".join(all_comments) if all_comments else "Yorum yok"
        
        user_msg = f"Ürün: {product_name}. Yorumlar: {comment_text[:4000]}. Analiz et ve JSON dön."
        
        payload = {
            "model": "llama-3.1-8b-instant", # Hız için 8B seçtik
            "messages": [
                {"role": "system", "content": "Sen NetPuan Analizörüsün. JSON formatında dürüst bir analiz raporu sun."},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=20)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        ai_data['platform'] = platform
        ai_data['urun_adi'] = product_name
        
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
