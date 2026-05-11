import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def trendyol_yorum_cek(url):
    try:
        # Linkten Ürün ID'sini çek (p-12345 formatı)
        match = re.search(r'p-(\d+)', url)
        if not match: return None
        content_id = match.group(1)
        
        # Trendyol Yorum API'sine istek at (İlk 15 yorum yeterli)
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{content_id}?page=0&size=15"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(api_url, headers=headers, timeout=10)
        data = response.json()
        
        # Sadece yorum metinlerini topla
        reviews = [r['comment'] for r in data.get('reviews', []) if 'comment' in r]
        return " | ".join(reviews)[:3000] # AI'ya çok yüklenmemek için sınırı koru
    except:
        return None

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    platform = "Genel"
    real_comments = ""

    # Eğer Trendyol linkiyse canlı yorum çek
    if "trendyol.com" in url:
        platform = "Trendyol"
        real_comments = trendyol_yorum_cek(url)

    # Ürün ismini linkten temizle
    product_raw = url.split('/')[-1].split('?')[0]
    product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()

    # AI'ya Gönderilecek Talimat (Prompt)
    system_prompt = f"Sen NetPuan AI analizörüsün. Ürün: {product_name}. Platform: {platform}."
    if real_comments:
        user_content = f"Aşağıdaki GERÇEK MÜŞTERİ YORUMLARINI analiz et ve manipülasyonu ayıklayarak dürüst bir özet ve 10 üzerinden puan ver.\n\nYORUMLAR:\n{real_comments}"
    else:
        user_content = f"Bu ürün ({product_name}) hakkındaki genel internet verilerini ve kullanıcı deneyimlerini analiz et."

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt + "\nJSON formatı: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'platform': '...', 'urun_adi': '...'}"},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"}
        }
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        res = requests.post(groq_url, json=payload, headers=headers, timeout=15)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
