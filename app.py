import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: 
        return jsonify({"hata": "Link eksik"}), 400

    try:
        # 1. Trendyol'dan Gerçek Veriyi Çekiyoruz
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Trendyol'un yorum başlıklarını veya metinlerini yakalıyoruz
        # Not: Trendyol bazen bu class isimlerini değiştirir, en yaygın olanları ekledik
        comment_elements = soup.find_all('div', class_='comment-text')
        comments = [c.text.strip() for c in comment_elements][:15] # İlk 15 yorumu al

        # Eğer yorum bulunamazsa boş gitmesin
        if not comments:
            comments_input = "Ürün yorumları bu sayfada doğrudan bulunamadı, genel bir değerlendirme yap."
        else:
            comments_input = " | ".join(comments)

        # 2. Groq API ile Gerçek Analiz
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
                    "content": "Sen profesyonel bir analizörsün. Sana gelen gerçek kullanıcı yorumlarını oku ve SADECE şu JSON formatında dürüst bir puanlama yap: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0}"
                },
                {"role": "user", "content": f"Şu gerçek yorumlara dayanarak dürüst ol: {comments_input}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post(groq_url, json=payload, headers=headers_groq, timeout=10)
        ai_data = json.loads(res.json()['choices'][0]['message']['content'])

        return jsonify(ai_data)

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
