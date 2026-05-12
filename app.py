import os
import requests
import json
import re
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def get_trendyol_comments(p_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'referer': 'https://www.trendyol.com/'}
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        res = requests.get(api_url, headers=headers, timeout=12)
        return [r['comment'] for r in res.json().get('reviews', []) if 'comment' in r] if res.status_code == 200 else []
    except: return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link eksik"}), 400

    all_comments = []
    product_name = "Ürün"
    platform = "Genel"

    if "http" in query:
        id_match = re.search(r'p-(\d+)', query)
        if "trendyol.com" in query:
            platform = "Trendyol"
            if id_match: all_comments.extend(get_trendyol_comments(id_match.group(1)))
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    comment_text = " | ".join(all_comments) if all_comments else "Canlı yorum yok, genel bilgi kullan."

    # --- YENİ TALİMATLAR (UZUN ANALİZ VE RAKİP ÖNERİSİ) ---
    prompt_instructions = f"""
    GÖREVİN:
    1. 'ozet' kısmını uzun tut (en az 3-4 cümle). Ürünün malzeme kalitesi, performansı ve fiyat dengesini detaylıca anlat.
    2. Puan ile Olumlu oranı tutarlı olsun (%80 olumluya 8 puan ver).
    3. 'en_iyi_alternatif' adında bir alan ekle. Bu ürünün kategorisindeki (örn: {product_name} bir kulaklıksa, kulaklık kategorisindeki) Türkiye piyasasında en çok övülen lider rakibi öner.
    4. 'istatistik_raporu' kısmında sayısal verileri (Kaç kişi kargo dedi vb.) net belirt.
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": f"Sen NetPuan Pro Analizörüsün. {prompt_instructions}"},
                {"role": "user", "content": f"Ürün: {product_name}. Yorumlar: {comment_text[:4000]}. JSON format: {{'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'istatistik_raporu': '...', 'en_sik_sikayet': '...', 'en_iyi_alternatif': '... (İsim ve Neden)'}}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        ai_data['platform'] = platform
        ai_data['urun_adi'] = product_name
        
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
