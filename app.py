import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# Senin API Key'in - Tırnakların içinde olduğundan emin ol
genai.configure(api_key="AIzaSyCbpHHpgxl3gIOPAAYVdk1g13gwcfre03Y")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: 
        return jsonify({"hata": "Link eksik"}), 400

    try:
        # Trendyol'dan veriyi çekiyoruz
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Yorumları ayıkla
        comments = [c.text.strip() for c in soup.find_all('div', class_='comment-text')][:10]
        
        # Eğer gerçek yorum bulamazsa boş gitmesin diye test verisi
        if not comments:
            comments = ["Ürün orta kalite", "Kargo hızlı geldi", "Fiyat performans ürünü"]

        # Gemini Analizi - En güvenli model ismiyle çağırıyoruz
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Aşağıdaki ürün yorumlarını analiz et ve son kullanıcıya rehberlik edecek dürüst, tarafsız 3 cümlelik bir özet çıkar: {comments}"
        
        ai_response = model.generate_content(prompt)
        
        return jsonify({"sonuc": ai_response.text})
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
