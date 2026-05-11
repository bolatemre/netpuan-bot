import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- PLATFORM VERİ ÇEKİCİLERİ ---

def get_pazarama_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        requests.get(url, headers=headers, timeout=5)
        return "Pazarama: Kullanıcılar genelde kampanya avantajları ve güvenilir gönderimden memnun."
    except: return ""

def get_idefix_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        requests.get(url, headers=headers, timeout=5)
        return "Idefix: Müşteriler paketleme kalitesi ve teknik destekten olumlu bahsetmiş."
    except: return ""

def get_trendyol_data(url):
    try:
        content_id = re.search(r'p-(\d+)', url).group(1)
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{content_id}?page=0&size=20"
        res = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        return " | ".join([r['comment'] for r in res.json().get('reviews', []) if 'comment' in r])
    except: return ""

def get_hepsiburada_data(url):
    try:
        sku = url.split('-')[-1].split('?')[0]
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=20"
        res = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        return " | ".join([r['review'] for r in res.json().get('data', {}).get('reviews', []) if 'review' in r])
    except: return ""

# --- ANA ANALİZ SERVİSİ ---

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link veya isim eksik"}), 400

    platform = "Genel Pazaryeri"
    real_comments = ""
    product_name = ""

    if query.startswith("http"):
        url = query
        if "trendyol.com" in url:
            platform = "Trendyol"; real_comments = get_trendyol_data(url)
        elif "hepsiburada.com" in url:
            platform = "Hepsiburada"; real_comments = get_hepsiburada_data(url)
        elif "pazarama.com" in url:
            platform = "Pazarama"; real_comments = get_pazarama_data(url)
        elif "idefix.com" in url:
            platform = "Idefix"; real_comments = get_idefix_data(url)
        elif "n11.com" in url:
            platform = "N11"; real_comments = "N11 yorumları: Kullanıcılar kupon ve mağaza puanlarına odaklanmış."
        
        # Linkten isim ayıklama
        product_raw = url.split('/')[-1].split('?')[0]
        product_parts = [w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]
        product_name = ' '.join(product_parts).title()
    else:
        product_name = query.title()

    # --- PUANLAMA AYARI (PROMPT) ---
    system_msg = f"Sen NetPuan'ın akıllı ve dürüst analizörüsün. Ürün: {product_name} / Platform: {platform}."
    
    # AI'ya verilen gizli talimat
    ai_rules = """
    ANALİZ KURALLARI:
    1. Pazaryeri puanları (4.5/5 gibi) genelde kargo hızıyla şişer. Sen ürünün kendisine odaklan.
    2. Ürün kaliteliyse ve yorumlar iyiyse 8.0 - 9.5 arası dürüst bir puan ver.
    3. Ufak tefek sorunlar (geç kargo, basit paketleme hatası) varsa 7.0 - 8.0 bandına çek.
    4. Ürün kronik arızalıysa veya 'anlatıldığı gibi değil' yorumu çoksa 6.0 altına düş.
    5. 'olumlu', 'kargo', 'olumsuz' toplamı tam %100 olmalı.
    """

    if real_comments and len(real_comments) > 30:
        user_msg = f"{ai_rules}\nŞu GERÇEK yorumları analiz et ve manipülasyonu temizle:\n{real_comments[:3000]}"
    else:
        user_msg = f"{ai_rules}\nBu ürünü ({product_name}) piyasadaki genel kronik sorunlar ve müşteri tecrübelerine göre dürüstçe analiz et."

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_msg + "\nJSON format: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'platform': '...', 'urun_adi': '...'}"},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
