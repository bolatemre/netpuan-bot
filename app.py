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

    comment_text = " | ".join(all_comments) if all_comments else "Canlı veri yok, genel uzmanlık bilginle yaz."

    # --- UZUN ANALİZ VE KATEGORİK DERİNLİK TALİMATLARI ---
    prompt_instructions = f"""
    ANALİZ KURALLARI (MÜŞTERİ ODAKLI):
    1. 'ozet' ALANINI ÇOK UZUN TUT: En az 150-200 kelime civarında, detaylı bir inceleme yazısı hazırla. 
    2. KATEGORİ ODAKLI OL: Eğer bu bir robot süpürge ise; emiş gücü, lidar sensör başarısı ve paspaslama gibi teknik detaylara gir. Kulaklıksa; bas/tiz dengesi ve ANC kalitesine değin.
    3. YORUM SENTEZİ: Kullanıcıların en çok dert yandığı veya en çok övdüğü teknik detayları 'Derin Analiz Özetinde' mutlaka belirt.
    4. KATEGORİ LİDERİ: 'en_iyi_alternatif' kısmında bu ürünün kategorisindeki en sağlam rakibi nedenleriyle öner.
    5. MATEMATİK: 'olumlu' + 'kargo' + 'olumsuz' toplamı tam 100 olmalı. Puan, olumlu oranıyla (10 üzerinden) paralel olmalı.
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-70b-versatile", # Daha uzun ve zeki cevaplar için 70B'ye geri çektik
            "messages": [
                {"role": "system", "content": f"Sen NetPuan Pro Üst Düzey Analizörüsün. {prompt_instructions}"},
                {"role": "user", "content": f"Ürün: {product_name}. Yorum Verileri: {comment_text[:4500]}. Detaylı bir JSON raporu sun."}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        res_data = res.json()

        # Fallback (70B hata verirse 8B'ye düş)
        if 'choices' not in res_data:
            payload["model"] = "llama-3.1-8b-instant"
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
            res_data = res.json()

        ai_data = json.loads(res_data['choices'][0]['message']['content'])
        
        # Matematiksel Düzeltme
        total = ai_data.get('olumlu', 0) + ai_data.get('kargo', 0) + ai_data.get('olumsuz', 0)
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
