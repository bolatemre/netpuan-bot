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
        # Trendyol'un bot sistemini şaşırtmak için rastgele User-Agent listesi
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        ]
        
        headers = {
            'User-Agent': random.choice(agents),
            'Accept': 'application/json',
            'Referer': 'https://www.trendyol.com/',
            'Origin': 'https://www.trendyol.com'
        }
        
        # Daha güvenli olan mobil inceleme API'sini deniyoruz
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        
        res = requests.get(api_url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            return [r['comment'] for r in data.get('reviews', []) if 'comment' in r]
        return []
    except:
        return []

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
            if id_match:
                p_id = id_match.group(1)
                all_comments.extend(get_trendyol_comments(p_id))
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    # --- KRİTİK NOKTA: VERİ YOKSA BİLE AI ANALİZİ ---
    if not all_comments:
        # Yorum çekilemediğinde devreye giren 'Profesyonel Tahmin' promptu
        user_msg = f"Bu ürün ({product_name}) hakkında Türkiye e-ticaret sitelerindeki genel kullanıcı şikayetlerini ve kronik sorunlarını biliyorsun. Şu an canlı yorum çekemedik ama sen genel bilgi birikimine göre dürüst bir analiz raporu ve 10 üzerinden skor üret."
    else:
        comment_text = " | ".join(all_comments)
        user_msg = f"Şu gerçek yorumları analiz et: {comment_text[:4000]}"

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant", # Hız için 8B
            "messages": [
                {"role": "system", "content": "Sen NetPuan Analizörüsün. Ürün hakkında dürüst bir JSON raporu sun. JSON format: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'istatistik_raporu': '...', 'en_sik_sikayet': '...'}"},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        ai_data['platform'] = platform
        ai_data['urun_adi'] = product_name
        
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
