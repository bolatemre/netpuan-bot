import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# Google'dan aldığın taze köprü URL'si
GOOGLE_PROXY_URL = "https://script.google.com/macros/s/AKfycbxr7k2dRTUiOvnl4QvS0g3smitkYwNtGg09lM9WB-BAhtGKY0TBZOoWzTNZ0OqH1Ezg/exec"

def get_trendyol_comments(p_id):
    try:
        # Trendyol API adresi
        target_url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        # Google köprüsü üzerinden istek atıyoruz
        res = requests.get(f"{GOOGLE_PROXY_URL}?url={requests.utils.quote(target_url)}", timeout=20)
        
        if res.status_code == 200:
            data = res.json()
            return [r['comment'] for r in data.get('reviews', []) if 'comment' in r]
        return []
    except Exception as e:
        print(f"Köprü Hatası: {e}")
        return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link veya isim eksik"}), 400

    all_comments = []
    platform_label = "Genel"
    product_name = "Ürün"

    # VERİ ÇEKME
    if "http" in query and "trendyol.com" in query:
        platform_label = "Trendyol"
        id_match = re.search(r'p-(\d+)', query)
        if id_match:
            all_comments = get_trendyol_comments(id_match.group(1))
        
        product_raw = query.split('/')[-1].split('?')[0]
        product_name = ' '.join([w for w in product_raw.split('-') if not w.startswith('p') and not w.isdigit()]).title()
    else:
        product_name = query.title()

    total_count = len(all_comments)
    comment_text = " | ".join(all_comments)

    # AI İÇİN ÖZEL TALİMATLAR
    prompt_rules = f"""
    Sen NetPuan Pro Analizörüsün.
    ÜRÜN: {product_name}
    GELEN VERİ: {total_count} adet gerçek müşteri yorumu çekildi.
    
    KURALLAR:
    1. KATEGORİ: Önce ürünün kategorisini KESİN doğru belirle (Örn: Koşu Bandı mı, Robot Süpürge mi?).
    2. DOĞRULUK: Eğer veri 0 ise uydurma özellik yazma. "{product_name} için pazar yerinden veri çekilemedi" uyarısı yap.
    3. ANALİZ: Yorumlar varsa; kronik sorunları, kargo şikayetlerini ve performans detaylarını UZUNCA yaz.
    4. RAKİP: Sadece aynı kategoriden (Eğer ürün Robot Süpürge ise başka bir robot süpürge) lider bir model öner.
    5. RAPOR: 'istatistik_raporu' alanına "Google Proxy aracılığıyla {total_count} adet yorum analiz edildi" yaz.
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": prompt_rules},
                {"role": "user", "content": f"Yorumlar: {comment_text[:4000]}. JSON formatında rapor sun."}
            ],
            "response_format": {"type": "json_object"}
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        # Matematik düzeltme
        total = ai_data.get('olumlu', 0) + ai_data.get('kargo', 0) + ai_data.get('olumsuz', 0)
        if total != 100 and total > 0:
            ai_data['olumlu'] = int((ai_data['olumlu'] / total) * 100)
            ai_data['kargo'] = int((ai_data['kargo'] / total) * 100)
            ai_data['olumsuz'] = 100 - (ai_data['olumlu'] + ai_data['kargo'])

        ai_data['platform'] = platform_label
        ai_data['urun_adi'] = product_name
        return jsonify(ai_data)
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
