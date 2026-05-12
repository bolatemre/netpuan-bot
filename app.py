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

    # Linkten veya metinden ürün ismini ayıkla
    if "http" in query:
        id_match = re.search(r'p-(\d+)', query)
        if "trendyol.com" in query:
            platform = "Trendyol"
            if id_match: all_comments.extend(get_trendyol_comments(id_match.group(1)))
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    comment_text = " | ".join(all_comments) if all_comments else "Canlı veri yok."

    # --- MATEMATİKSEL VE KATEGORİK TALİMATLAR ---
    prompt_instructions = f"""
    SİSTEM KURALLARI:
    1. ÜRÜN TANIMA: Önce '{product_name}' ürününün hangi kategoriye (örn: Robot Süpürge, Akıllı Saat) ait olduğunu belirle. 
    2. KATEGORİ LİDERİ: Bu kategorideki (Türkiye piyasasında) en yüksek puanlı, sorunsuz 'Amiral Gemisi' ürünü 'en_iyi_alternatif' olarak öner.
    3. MATEMATİK: 'olumlu' + 'kargo' + 'olumsuz' toplamı HER ZAMAN TAM 100 olmalıdır. Saçma sapan rakamlar verme.
    4. PUAN UYUMU: Puan (10 üzerinden), olumlu yüzdesiyle paralel olmalı. %90 olumluya 9.0, %50 olumluya 5.0 puan ver.
    5. DETAY: 'ozet' kısmında kategorik özelliklere değin (örn robot süpürge ise emiş gücü, haritalama gibi).
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": f"Sen NetPuan Pro Analizörüsün. {prompt_instructions}"},
                {"role": "user", "content": f"Ürün: {product_name}. Veriler: {comment_text[:4000]}. JSON format: {{'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'istatistik_raporu': '...', 'en_sik_sikayet': '...', 'en_iyi_alternatif': '...'}}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        # Yüzdeliklerin toplamını kontrol et ve gerekirse düzelt (Matematiksel Sağlamlaştırma)
        total = ai_data['olumlu'] + ai_data['kargo'] + ai_data['olumsuz']
        if total != 100 and total > 0:
            ai_data['olumlu'] = int((ai_data['olumlu'] / total) * 100)
            ai_data['kargo'] = int((ai_data['kargo'] / total) * 100)
            ai_data['olumsuz'] = 100 - (ai_data['olumlu'] + ai_data['kargo'])

        ai_data['platform'] = platform
        ai_data['urun_adi'] = product_name
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
