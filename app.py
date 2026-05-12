import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# PROFESYONEL İPUCU: Trendyol bloklarını aşmak için 'Proxy' kullanılması şarttır.
# Eğer bir Proxy servisi alırsan buraya ekleyebilirsin.
PROXIES = {
    # "http": "http://username:password@proxy_host:port",
    # "https": "http://username:password@proxy_host:port"
}

def get_trendyol_comments(p_id):
    try:
        # Trendyol Mobil Uygulaması gibi davranan en üst düzey Header seti
        headers = {
            'User-Agent': 'TrendyolMobileApp/5.11.0 (iPhone; iOS 17.4; Scale/3.00)',
            'Accept': 'application/json',
            'Host': 'public-mdc.trendyol.com',
            'X-Mobile-Platform': 'ios',
            'Accept-Language': 'tr-TR'
        }
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        
        # İstek gönderiliyor (Proxy varsa proxies=PROXIES eklenir)
        res = requests.get(api_url, headers=headers, timeout=12)
        
        if res.status_code == 200:
            data = res.json()
            comments = [r['comment'] for r in data.get('reviews', []) if 'comment' in r]
            return comments
        return []
    except Exception as e:
        print(f"Trendyol Hata: {e}")
        return []

def get_hepsiburada_comments(sku):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=50"
        res = requests.get(api_url, headers=headers, timeout=12)
        if res.status_code == 200:
            return [r['review'] for r in res.json().get('data', {}).get('reviews', []) if 'review' in r]
        return []
    except Exception as e:
        print(f"HB Hata: {e}")
        return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link veya isim eksik"}), 400

    platform_counts = {"Trendyol": 0, "Hepsiburada": 0}
    all_comments = []
    product_name = "Ürün"
    platform_label = "Genel"

    if "http" in query:
        if "trendyol.com" in query:
            platform_label = "Trendyol"
            id_match = re.search(r'p-(\d+)', query)
            if id_match:
                comments = get_trendyol_comments(id_match.group(1))
                all_comments.extend(comments)
                platform_counts["Trendyol"] = len(comments)
        elif "hepsiburada.com" in query:
            platform_label = "Hepsiburada"
            sku = query.split('-')[-1].split('?')[0]
            comments = get_hepsiburada_comments(sku)
            all_comments.extend(comments)
            platform_counts["Hepsiburada"] = len(comments)
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    total_count = len(all_comments)
    comment_text = " | ".join(all_comments)

    # --- PROFESYONEL AI TALİMATI ---
    prompt_rules = f"""
    Sen NetPuan Ticari Analiz Uzmanısın. 
    1. KATEGORİ: Ürünün ({product_name}) kategorisini KESİN doğru belirle. Yanlış kategoriye ait özellik yazma.
    2. VERİ DURUMU: Trendyol'dan {platform_counts['Trendyol']}, HB'den {platform_counts['Hepsiburada']} yorum geldi.
    3. STRATEJİ: Eğer toplam veri 0 ise, halüsinasyon görme. Sadece "{product_name} için pazar yerlerinden canlı veri alınamadı, genel kategori standartlarına göre değerlendiriliyor" de.
    4. RAKİP: Sadece aynı kategoriden amiral gemisi bir rakip öner.
    5. RAPOR: 'istatistik_raporu' alanına hangi platformdan kaç yorum çekildiğini net yaz.
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": prompt_rules},
                {"role": "user", "content": f"Yorumlar: {comment_text[:4000]}. JSON formatında rapor ver."}
            ],
            "response_format": {"type": "json_object"}
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        ai_data['platform'] = platform_label
        ai_data['urun_adi'] = product_name
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
