import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- VERİ ÇEKME FONKSİYONLARI ---
def get_trendyol_comments(p_id):
    try:
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=30"
        res = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        return [r['comment'] for r in res.json().get('reviews', []) if 'comment' in r]
    except:
        return []

def get_hepsiburada_comments(sku):
    try:
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=30"
        res = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        return [r['review'] for r in res.json().get('data', {}).get('reviews', []) if 'review' in r]
    except:
        return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query:
        return jsonify({"hata": "Link veya isim eksik"}), 400

    all_comments = []
    product_name = ""
    platform = "Genel"

    if "http" in query:
        if "trendyol.com" in query:
            platform = "Trendyol"
            match = re.search(r'p-(\d+)', query)
            if match:
                p_id = match.group(1)
                all_comments.extend(get_trendyol_comments(p_id))
        elif "hepsiburada.com" in query:
            platform = "Hepsiburada"
            sku = query.split('-')[-1].split('?')[0]
            all_comments.extend(get_hepsiburada_comments(sku))
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    comment_text = " | ".join(all_comments)
    total_count = len(all_comments)

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        system_msg = f"Sen NetPuan Veri Analiz Uzmanısın. Ürün: {product_name}."
        user_msg = f"Aşağıdaki {total_count} adet gerçek yorumu analiz et. Kaç kişi kargo, kaç kişi kalite dedi say. JSON format: {{'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'istatistik_raporu': '...', 'en_sik_sikayet': '...'}}\n\nYORUMLAR: {comment_text[:4500]}"
        
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        res_data = res.json()

        if 'choices' not in res_data:
            payload["model"] = "llama-3.1-8b-instant"
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
            res_data = res.json()

        ai_data = json.loads(res_data['choices'][0]['message']['content'])
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
