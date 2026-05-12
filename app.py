import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GOOGLE_PROXY_URL = "https://script.google.com/macros/s/AKfycbzWIyrBeTQWP5XA-kkoOhX_VTwO8XlYW43hift0l8_SNG0Ig2utlbA4TbBGx2CY5rS3/exec"

def get_trendyol_comments(p_id):
    try:
        api_link = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/reviews/{p_id}?page=0&size=50"
        res = requests.get(f"{GOOGLE_PROXY_URL}?url={requests.utils.quote(api_link)}", timeout=25)
        if res.status_code == 200:
            data = res.json()
            # Trendyol bazen boş liste döner, kontrol et
            return [r['comment'] for r in data.get('reviews', []) if 'comment' in r]
        return []
    except: return []

@app.route('/analiz', methods=['GET'])
def analiz_et():
    query = request.args.get('url')
    if not query: return jsonify({"hata": "Link veya isim eksik"}), 400

    all_comments = []
    platform_label = "Genel"
    product_name = ""

    # 1. ADIM: VERİ ÇEKMEYİ DENE
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
    
    # 2. ADIM: AI'YA DURUMU NET ANLAT (MODERN PROMPT)
    # Eğer yorum yoksa AI'ya "Genel Piyasa Verisini Kullan" diyoruz
    if total_count > 0:
        data_source = f"Şu an çekilen {total_count} adet GERÇEK müşteri yorumunu analiz et."
        comment_payload = " | ".join(all_comments)[:4000]
    else:
        data_source = f"Canlı yorum çekilemedi. {product_name} hakkındaki GENEL PİYASA BİLGİNİ VE KRONİK SORUNLARI kullanarak analiz yap."
        comment_payload = "Veri yok, genel bilgi kullan."

    prompt_rules = f"""
    GÖREV: {product_name} için profesyonel analiz raporu hazırla.
    KAYNAK: {data_source}
    
    KESİN KURALLAR:
    1. KATEGORİ: Önce ürünün kategorisini belirle. Robot süpürgeye alakasız özellik yazma.
    2. PUANLAMA: Olumlu yüzdeyle puan uyumlu olsun (%85 olumlu = 8.5 puan). Toplam %100 olsun.
    3. ÖZET: En az 150 kelime. Ürünün donanımı, yazılımı ve rakip avantajlarını detaylandır.
    4. RAKİP: Sadece AYNI KATEGORİDEN (örn: başka bir robot süpürge) lider model öner.
    5. RAPOR: 'istatistik_raporu' alanına '{total_count} canlı yorum + piyasa verileri harmanlandı' yaz.
    """

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": prompt_rules},
                {"role": "user", "content": f"Ürün: {product_name}. Veriler: {comment_payload}. JSON Raporu sun."}
            ],
            "response_format": {"type": "json_object"}
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=25)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])
        
        # Matematiksel Doğrulama
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
