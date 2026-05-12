import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- GELİŞMİŞ VERİ TOPLAMA FONKSİYONLARI ---

def get_trendyol_comments(p_id):
    try:
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=30"
        res = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        return [r['comment'] for r in res.json().get('reviews', []) if 'comment' in r]
    except: return []

def get_hepsiburada_comments(sku):
    try:
        # SKU üzerinden HB yorumlarını çekme
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=30"
        res = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        return [r['review'] for r in res.json().get('data', {}).get('reviews', []) if 'review' in r]
    except: return []

# --- ANA ANALİZ MOTORU ---

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link veya isim eksik"}), 400

    all_comments = []
    product_name = ""
    
    # 1. ADIM: ANA KAYNAKTAN VERİ ÇEK VE İSİM BUL
    if "trendyol.com" in query:
        p_id = re.search(r'p-(\d+)', query).group(1)
        all_comments.extend(get_trendyol_comments(p_id))
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
        
        # HARMANLAMA (Trendyol linki varken Hepsiburada'da da "aynı" SKU'yu bulmaya çalışır)
        # Gerçek bir sistemde burada ürün ismiyle HB'de arama yapan bir fonksiyon çalışır.
        # Şimdilik ana veriye odaklanıp istatistik raporunu güçlendiriyoruz.

    elif "hepsiburada.com" in query:
        sku = query.split('-')[-1].split('?')[0]
        all_comments.extend(get_hepsiburada_comments(sku))
        product_name = "Ürün Analizi"

    # 2. ADIM: PROFESYONEL ANALİZ VE SAYISAL RAPOR
    comment_text = " | ".join(all_comments)
    
    system_msg = f"Sen NetPuan Veri Analiz Uzmanısın. Ürün: {product_name}."
    
    # AI'ya sayısal rapor zorunluluğu getiriyoruz
    user_msg = f"""
    Aşağıdaki yorumları çok titiz bir şekilde analiz et. 
    Sana verilen yorumları tek tek oku ve şu formatta bir 'istatistik_raporu' oluştur:
    
    GÖREVLER:
    1. Kaç kişi kargodan şikayet etmiş? (Tam sayı ver)
    2. Kaç kişi ürünün kalitesini/performansını övmüş? (Tam sayı ver)
    3. Kaç kişi iade veya kusurlu ürün bildirmiş? (Tam sayı ver)
    4. Ürünün en çok eleştirilen noktası nedir?
    
    PUANLAMA: 10 üzerinden çok dürüst yap. 
    
    YORUMLAR:
    {comment_text[:4500]}
    """

    try:
        payload = {
            "model": "llama-3.1-70b-versatile", # Daha güçlü model, daha iyi sayar
            "messages": [
                {
                    "role": "system", 
                    "content": system_msg + "\nJSON formatında dön: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'istatistik_raporu': '12 kişi kargo sorunu, 25 kişi kalite onayı bildirdi', 'en_cok_konusulan': 'Batarya ömrü'}"
                },
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
