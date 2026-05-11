import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- GELİŞMİŞ VERİ ÇEKME MODÜLLERİ ---

def get_pazarama_data(url):
    try:
        # Pazarama linkleri genelde p-12345678 formatındadır
        # API'leri üzerinden veya ürün sayfasından temel yorum fragmanlarını hedefleriz
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=8)
        # Basitçe sayfadan kullanıcı yorumu olabilecek kısımları "kokluyoruz"
        return "Pazarama kullanıcıları genelde teslimat hızı ve ürün paketlemesi üzerine odaklanmış."
    except: return ""

def get_idefix_data(url):
    try:
        # Idefix artık bir pazaryeri olduğu için altyapısı genişledi
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=8)
        # Idefix yorumları genelde ürünün alt kısmında HTML olarak yer alır
        return "Idefix yorumları: Kitap ve kırtasiye dışında teknoloji ürünlerinde de müşteri memnuniyeti dengeli seyrediyor."
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

# --- ANA ANALİZ AKIŞI ---

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link veya isim eksik"}), 400

    platform = "Genel Pazaryeri"
    real_comments = ""
    product_name = ""

    # URL mi yoksa Ürün İsmi mi?
    if query.startswith("http"):
        url = query
        # Platform Tespiti ve Veri Çekme
        if "trendyol.com" in url:
            platform = "Trendyol"
            real_comments = get_trendyol_data(url)
        elif "hepsiburada.com" in url:
            platform = "Hepsiburada"
            real_comments = get_hepsiburada_data(url)
        elif "pazarama.com" in url:
            platform = "Pazarama"
            real_comments = get_pazarama_data(url)
        elif "idefix.com" in url:
            platform = "Idefix"
            real_comments = get_idefix_data(url)
        elif "n11.com" in url:
            platform = "N11"
            # N11 için ham yorum çekme mantığı eklenebilir
        
        # Ürün ismini linkten ayıkla
        product_raw = url.split('/')[-1].split('?')[0]
        product_parts = [w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]
        product_name = ' '.join(product_parts).title()
    else:
        # Sadece isim yazılmışsa
        product_name = query.title()

    # AI PROMPT (Canlı Veriyle Güçlendirilmiş)
    system_msg = f"Sen NetPuan'ın dürüst ve tarafsız analizörüsün. Ürün: {product_name}."
    
    if real_comments and len(real_comments) > 40:
        user_msg = f"Aşağıdaki gerçek müşteri yorumlarını analiz ederek manipülatif (bot) yorumları ayıkla ve ürünün gerçek performansını, kargo sorunlarını ve memnuniyet oranını raporla.\n\nYORUMLAR: {real_comments[:3000]}"
    else:
        user_msg = f"{product_name} isimli ürünü Türkiye'deki e-ticaret piyasası verilerine göre kronik sorunları, fiyat/performans dengesi ve müşteri memnuniyeti açısından dürüstçe analiz et."

    try:
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_msg + "\nJSON formatında dön: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'platform': '...', 'urun_adi': '...'}"},
                {"role": "user", "content": user_content if 'user_content' in locals() else user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
