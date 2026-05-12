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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=40"
        res = requests.get(api_url, headers=headers, timeout=8)
        if res.status_code == 200:
            return [r['comment'] for r in res.json().get('reviews', []) if 'comment' in r]
        return []
    except:
        return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query:
        return jsonify({"hata": "Link veya isim eksik"}), 400

    all_comments = []
    product_name = "Ürün"
    platform = "Genel"

    if "http" in query:
        id_match = re.search(r'p-(\d+)', query)
        if "trendyol.com" in query:
            platform = "Trendyol"
            if id_match:
                all_comments.extend(get_trendyol_comments(id_match.group(1)))
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    comment_text = " | ".join(all_comments) if all_comments else "Canlı yorum yok, genel uzmanlık bilginle detaylı yaz."

    # Hız ve uzunluk dengesi için optimize edilmiş talimat
    prompt_instructions = f"""
    Sen NetPuan Pro Analizörüsün. Ürün: {product_name}.
    KURALLAR:
    1. 'ozet' alanını oldukça uzun ve detaylı tut (cihazın teknik özellikleri, kullanıcı deneyimi, artıları ve eksileri).
    2. 'en_iyi_alternatif' kısmında bu ürünün kategorisindeki en güçlü rakibi öner.
    3. Matematik: 'olumlu' + 'kargo' + 'olumsuz' toplamı tam 100 olmalı. Puan, olumlu oranıyla uyumlu olmalı.
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant", # Hız için 8B kullanıyoruz, timeout hatasını önler
            "messages": [
                {"role": "system", "content": prompt_instructions},
                {"role": "user", "content": f"Veriler: {comment_text[:4000]}. Detaylı JSON raporu sun."}
            ],
            "response_format": {"type": "json_object"}
        }
        
        # Zaman aşımını önlemek için timeout değerini artırdık
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        res_data = res.json()
        
        if 'choices' not in res_data:
            return jsonify({"hata": "Groq API yanıt vermedi"}), 500

        ai_data = json.loads(res_data['choices'][0]['message']['content'])
        
        # Matematiksel Doğrulama
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
