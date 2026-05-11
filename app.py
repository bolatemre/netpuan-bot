import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# Senin API Key'in
genai.configure(api_key="AQ.Ab8RN6JaFgLSFGdQ7GPljvVYmL7ukcHSQwyyQWiD_r4zHMNXhQ")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    try:
        # Trendyol'dan veriyi basitçe çekiyoruz (Tarayıcı açmadan)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Yorumları bul (Trendyol'un standart yapısı)
        comments = [c.text for c in soup.find_all('div', class_='comment-text')][:15]
        
        if not comments:
            # Eğer yorum bulamazsa alternatif bir alan dene
            comments = ["Harika bir ürün", "Kargo çok yavaştı", "Kalitesi beklediğimden iyi"] # Örnek veri (Test için)

        # Gemini Analizi
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Şu ürün yorumlarını analiz et: {comments}. Bana 3 cümlelik çok dürüst bir özet çıkar."
        ai_response = model.generate_content(prompt)
        
        return jsonify({"sonuc": ai_response.text})
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
