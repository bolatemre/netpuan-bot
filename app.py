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
        # Trendyol bu sefer kaçmasın diye header'ları tam bir Chrome tarayıcı gibi süsledik
        headers = {
            'authority': 'public-mdc.trendyol.com',
            'accept': 'application/json, text/plain, */*',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'origin': 'https://www.trendyol.com',
            'referer': 'https://www.trendyol.com/',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        # Sayfa başı 50 yorum çekmeyi deneyelim
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        
        # SSL doğrulamasını (verify=False) bazen Render'da gerekebilir ama önce böyle deneyelim
        res = requests.get(api_url, headers=headers, timeout=12)
        
        if res.status_code == 200:
            data = res.json()
            comments = [r['comment'] for r in data.get('reviews', []) if 'comment' in r]
            print(f"Başarılı! {len(comments)} yorum çekildi.")
            return comments
        else:
            print(f"Trendyol Engelledi! Kod: {res.status_code}")
            return []
    except Exception as e:
        print(f"Hata: {str(e)}")
        return []

def get_hepsiburada_comments(sku):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        api_url = f"https://customer-reviews-v2.hepsiburada.com/api/v1/product-reviews/{sku}/reviews?sort=Standard&page=1&size=40"
        res = requests.get(api_url, headers=headers, timeout=10)
        return [r['review'] for r in res.json().get('data', {}).get('reviews', []) if 'review' in r]
    except: return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link eksik"}), 400

    all_comments = []
    product_name = "Ürün"
    platform = "Genel"

    if "http" in query:
        # Regex'i garantiye alalım
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
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    total_count = len(all_comments)
    
    # --- YORUM ÇEKİLEMEDİYSE ACİL DURUM PLANI ---
    if total_count == 0:
        # Eğer yorum çekemediysek AI'ya 'Genel Bilgi' ile analiz yapmasını söylüyoruz
        user_msg = f"Bu ürün ({product_name}) hakkında internetteki genel kullanıcı şikayetlerini ve kronik sorunlarını analiz et. Elimde şu an canlı yorum yok ama sen genel piyasa verisinden dürüst bir skor çıkar."
    else:
        comment_text = " | ".join(all_comments)
        user_msg = f"Aşağıdaki {total_count} gerçek yorumu analiz et. JSON dön: {{'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'istatistik_raporu': '...', 'en_sik_sikayet': '...', 'urun_adi': '{product_name}'}}\n\nYORUMLAR: {comment_text[:4500]}"

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [
                {"role": "system", "content": f"Sen NetPuan Analizörüsün. Ürün: {product_name}."},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        res_data = res.json()

        if 'choices' not in res_data:
            payload["model"] = "llama-3.1-8b-instant"
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
            res_data = res.json()

        ai_data = json.loads(res_data['choices'][0]['message']['content'])
        ai_data['platform'] = platform
        if 'urun_adi' not in ai_data: ai_data['urun_adi'] = product_name
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
