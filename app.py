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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'referer': 'https://www.trendyol.com/'
        }
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        res = requests.get(api_url, headers=headers, timeout=12)
        if res.status_code == 200:
            return [r['comment'] for r in res.json().get('reviews', []) if 'comment' in r]
        return []
    except: return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link eksik"}), 400

    all_comments = []
    product_name = "Ürün"
    platform_info = "Genel"

    if "http" in query:
        id_match = re.search(r'p-(\d+)', query)
        if "trendyol.com" in query:
            platform_info = "Trendyol"
            if id_match:
                comments = get_trendyol_comments(id_match.group(1))
                all_comments.extend(comments)
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    total_count = len(all_comments)
    comment_text = " | ".join(all_comments)

    # --- VERİ DOĞRULAMA VE KATEGORİ TALİMATI ---
    prompt_instructions = f"""
    SİSTEM VE VERİ KURALLARI:
    1. KİMLİK TESPİTİ: '{product_name}' ürününün kategorisini (örn: Koşu Bandı, Kulaklık vb.) KESİN doğru belirle. Koşu bandına robot süpürge özelliği yazarsan sistem çöker.
    2. VERİ KANITI: Okuduğun yorum sayısı: {total_count}. Eğer bu sayı 0 ise 'Yorum bulunamadı' de ve piyasa bilgine başvur ama uydurma.
    3. RAKİP ANALİZİ: 'en_iyi_alternatif' kısmına sadece AYNI KATEGORİDEN (Koşu bandı ise koşu bandı) profesyonel bir rakip öner. Yoga matı gibi alakasız ürünler yasaktır.
    4. MATEMATİK: 'olumlu' + 'kargo' + 'olumsuz' = TAM 100 olmalı. Puan 10 üzerinden olmalı.
    5. RAPOR: 'istatistik_raporu' kısmında şunu yaz: '{total_count} adet gerçek yorum analiz edildi. Yorumların ana odak noktaları şunlar...'
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": f"Sen NetPuan Pro Analizörüsün. Sadece gerçek verilere dayalı konuşursun. {prompt_instructions}"},
                {"role": "user", "content": f"Ürün: {product_name}. Platform: {platform_info}. Veriler: {comment_text[:4500]}. JSON formatında rapor sun."}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        # Matematik Düzeltme
        total = ai_data.get('olumlu', 0) + ai_data.get('kargo', 0) + ai_data.get('olumsuz', 0)
        if total != 100 and total > 0:
            ai_data['olumlu'] = int((ai_data['olumlu'] / total) * 100)
            ai_data['kargo'] = int((ai_data['kargo'] / total) * 100)
            ai_data['olumsuz'] = 100 - (ai_data['olumlu'] + ai_data['kargo'])

        ai_data['platform'] = platform_info
        ai_data['urun_adi'] = product_name
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
