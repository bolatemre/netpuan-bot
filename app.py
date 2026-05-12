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
        headers = {'User-Agent': 'Mozilla/5.0'}
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=40"
        res = requests.get(api_url, headers=headers, timeout=10)
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

    comment_text = " | ".join(all_comments) if all_comments else "Canlı veri yok."

    # Çok daha detaylı ve uzun analiz talimatı
    p_rules = f"""
    Sen bir Alışveriş Uzmanısın. Ürün: {product_name}. 
    KURALLAR:
    1. 'ozet' kısmını oldukça uzun, teknik detaylı ve kullanıcı dostu yaz.
    2. 'en_iyi_alternatif' kısmında bu ürünün kategorisindeki (örn: {product_name} bir saatse, en iyi saat rakibini) öner.
    3. 'olumlu'+'kargo'+'olumsuz' = 100 olmalı. Puan, olumlu oranıyla uyumlu olmalı.
    """

    models = ["llama-3.1-8b-instant", "llama-3.1-70b-versatile"] # İki modeli de listeye aldık
    
    for model in models:
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": p_rules}, {"role": "user", "content": f"Yorumlar: {comment_text[:4000]}. JSON formatında detaylı rapor sun."}],
                "response_format": {"type": "json_object"}
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=20)
            
            if res.status_code == 200:
                ai_data = json.loads(res.json()['choices'][0]['message']['content'])
                
                # Matematiksel Doğrulama
                total = ai_data.get('olumlu', 0) + ai_data.get('kargo', 0) + ai_data.get('olumsuz', 0)
                if total != 100 and total > 0:
                    ai_data['olumlu'] = int((ai_data['olumlu'] / total) * 100)
                    ai_data['kargo'] = int((ai_data['kargo'] / total) * 100)
                    ai_data['olumsuz'] = 100 - (ai_data['olumlu'] + ai_data['kargo'])

                ai_data['platform'] = platform
                ai_data['urun_adi'] = product_name
                return jsonify(ai_data)
        except:
            continue # İlk model hata verirse döngü devam eder, diğerini dener

    return jsonify({"hata": "Groq şu an yanıt vermiyor, lütfen 10 saniye sonra tekrar deneyin."}), 503

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
