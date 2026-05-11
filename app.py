import os
import requests
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Render Environment'dan Groq anahtarını çekiyoruz
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def trendyol_yorum_cek(url):
    try:
        # Linkten ürün ID'sini bul (p-12345 kısmı)
        match = re.search(r"p-(\d+)", url)
        if not match:
            return None
        
        product_id = match.group(1)
        # Trendyol'un yorumları çektiği resmi API
        api_url = f"https://public-mdc.trendyol.com/discovery-web-socialview-service/api/reviews/{product_id}?storefrontId=1&culture=tr-TR&order=5&searchValue=&showOnlyConfirmedReviews=true&page=0"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        res = requests.get(api_url, headers=headers, timeout=10)
        data = res.json()
        
        # Sadece yorum metinlerini alıyoruz
        comments = []
        if 'content' in data:
            for item in data['content']:
                if 'comment' in item and item['comment']:
                    comments.append(item['comment'])
        
        return " | ".join(comments[:20]) # İlk 20 yorumu birleştir
    except Exception as e:
        print(f"Veri çekme hatası: {e}")
        return None

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: 
        return jsonify({"hata": "Link eksik"}), 400

    # 1. Gerçek yorumları çek
    raw_comments = trendyol_yorum_cek(url)
    
    # Eğer yorum gelmediyse AI'ya durumu bildir
    if not raw_comments:
        raw_comments = "HATA: Yorumlar çekilemedi. Lütfen kullanıcıya 'Yorumlar şu an okunamıyor' bilgisi ver."

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers_groq = {
            "Authorization": f"Bearer {GROQ_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": """Sen dürüst ve tarafsız bir analizörsün. 
                    Sana gelen yorumları oku. Eğer 'HATA' mesajı gelmişse puanları 0 yap ve özette hatayı belirt.
                    Eğer yorumlar gelmişse; kargo, kalite ve memnuniyet oranlarını dürüstçe hesapla.
                    Cevabını SADECE şu JSON formatında ver: 
                    {"ozet": "...", "puan": 8.5, "olumlu": 85, "kargo": 90, "olumsuz": 10}"""
                },
                {"role": "user", "content": f"Şu yorumları analiz et: {raw_comments}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(groq_url, json=payload, headers=headers_groq, timeout=10)
        ai_response = response.json()
        
        # AI'dan gelen JSON metnini ayrıştır
        result = json.loads(ai_response['choices'][0]['message']['content'])
        return jsonify(result)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
