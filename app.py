import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- GÜÇLÜ VERİ ÇEKME FONKSİYONLARI ---

def get_trendyol_comments(p_id):
    try:
        # Trendyol bot korumasını geçmek için sağlam header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.trendyol.com/'
        }
        # Popüler ve gerçek 40 yorumu çekiyoruz (size=40)
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=40"
        res = requests.get(api_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            return [r['comment'] for r in data.get('reviews', []) if 'comment' in r and len(r['comment']) > 5]
        return []
    except:
        return []

def get_hepsiburada_comments(sku):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=40"
        res = requests.get(api_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return [r['review'] for r in data.get('data', {}).get('reviews', []) if 'review' in r]
        return []
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

    # 1. ADIM: VERİ TOPLAMA
    if "http" in query:
        # Daha geniş kapsamlı ID yakalayıcı (p-12345 formatı için)
        id_match = re.search(r'p-(\d+)', query)
        
        if "trendyol.com" in query:
            platform = "Trendyol"
            if id_match:
                p_id = id_match.group(1)
                all_comments.extend(get_trendyol_comments(p_id))
        elif "hepsiburada.com" in query:
            platform = "Hepsiburada"
            sku = query.split('-')[-1].split('?')[0]
            all_comments.extend(get_hepsiburada_comments(sku))
        
        # Ürün ismini linkten temizle
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    total_count = len(all_comments)
    comment_text = " | ".join(all_comments)

    # 2. ADIM: YORUM YOKSA AI'YA GİTMEDEN CEVAP VER (0.0 PUAN SORUNU ÇÖZÜMÜ)
    if total_count == 0 and "http" in query:
        return jsonify({
            "ozet": f"Bu {platform} ürünü için henüz yazılı müşteri yorumu çekilemedi. Ürün çok yeni olabilir veya teknik bir engel oluştu.",
            "puan": 0.0,
            "olumlu": 0, "kargo": 0, "olumsuz": 0,
            "platform": platform,
            "urun_adi": product_name,
            "istatistik_raporu": "Veri toplanamadığı için istatistik oluşturulamadı.",
            "en_sik_sikayet": "Yorum Bulunamadı"
        })

    # 3. ADIM: AI ANALİZ (LLAMA 70B & 8B Fallback)
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        system_msg = f"Sen NetPuan Veri Analiz Uzmanısın. Ürün: {product_name}. Kesinlikle JSON dön."
        
        user_msg = f"Aşağıdaki {total_count} adet gerçek yorumu analiz et. Sayısal rapor çıkar. JSON format: {{'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'istatistik_raporu': '...', 'en_sik_sikayet': '...', 'urun_adi': '{product_name}'}}\n\nYORUMLAR: {comment_text[:4500]}"
        
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        res_data = res.json()

        if 'choices' not in res_data:
            payload["model"] = "llama-3.1-8b-instant"
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
            res_data = res.json()

        ai_content = res_data['choices'][0]['message']['content']
        ai_data = json.loads(ai_content)
        ai_data['platform'] = platform
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
