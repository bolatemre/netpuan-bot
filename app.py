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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=40"
        res = requests.get(api_url, headers=headers, timeout=10)
        if res.status_code == 200:
            return [r['comment'] for r in res.json().get('reviews', []) if 'comment' in r]
        return []
    except: return []

def get_hepsiburada_comments(sku):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=40"
        res = requests.get(api_url, headers=headers, timeout=10)
        if res.status_code == 200:
            return [r['review'] for r in res.json().get('data', {}).get('reviews', []) if 'review' in r]
        return []
    except: return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link veya isim eksik"}), 400

    results = {"Trendyol": 0, "Hepsiburada": 0}
    all_comments = []
    product_name = "Ürün"
    platform_name = "Genel"

    # VERİ ÇEKME AŞAMASI
    if "http" in query:
        if "trendyol.com" in query:
            platform_name = "Trendyol"
            id_match = re.search(r'p-(\d+)', query)
            if id_match:
                comments = get_trendyol_comments(id_match.group(1))
                all_comments.extend(comments)
                results["Trendyol"] = len(comments)
        elif "hepsiburada.com" in query:
            platform_name = "Hepsiburada"
            sku = query.split('-')[-1].split('?')[0]
            comments = get_hepsiburada_comments(sku)
            all_comments.extend(comments)
            results["Hepsiburada"] = len(comments)
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    total_count = len(all_comments)
    comment_text = " | ".join(all_comments)

    # AI TALİMATI (KESİN VE NET)
    prompt = f"""
    Sen dürüst bir analizörsün. Ürün: {product_name}. 
    KATEGORİ TESPİTİ: Bu ürünün tam kategorisini anla.
    VERİ DURUMU: Toplam {total_count} yorum çekildi. (Trendyol: {results['Trendyol']}, HB: {results['Hepsiburada']})
    KURAL 1: Eğer veri 0 ise 'Canlı yorum çekilemedi' de ve genel piyasa bilgini kullan ama teknik özellikleri uydurma.
    KURAL 2: Alternatif olarak sadece AYNI KATEGORİDEN lider ürün öner.
    KURAL 3: 'istatistik_raporu' kısmına şunu yaz: 'Trendyol'dan {results['Trendyol']}, Hepsiburada'dan {results['Hepsiburada']} yorum analiz edildi.'
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Yorumlar: {comment_text[:4000]}. JSON formatında rapor ver."}
            ],
            "response_format": {"type": "json_object"}
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=20)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        ai_data['platform'] = platform_name
        ai_data['urun_adi'] = product_name
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
