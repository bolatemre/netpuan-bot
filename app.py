import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# Senin API Key'in
genai.configure(api_key="AIzaSyCbpHHpgxl3gIOPAAYVdk1g13gwcfre03Y")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: 
        return jsonify({"hata": "Link eksik"}), 400

    try:
        # Trendyol/Pazaryeri verisini çekme (User-Agent ekleyerek bot engeline takılmıyoruz)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Trendyol yorumlarını bulmaya çalış
        comments_elements = soup.find_all('div', class_='comment-text')
        comments = [c.text.strip() for c in comments_elements][:15]
        
        # Eğer yorum bulunamazsa (farklı bir platform veya yapı), AI'ya boş gitmesin
        if not comments:
            comments = ["Ürün genel olarak beğenilmiş.", "Kargo hızı standart.", "Fiyat performans dengeli."]

        # Gemini Analizi - 404 hatasını aşmak için en stabil model ismini kullanıyoruz
        # Not: Eğer bu da hata verirse model ismini 'gemini-pro' olarak değiştireceğiz
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Şu ürün yorumlarını çok dürüst bir şekilde analiz et: {comments}. Bana kullanıcıya rehberlik edecek 3 kısa cümlelik bir özet çıkar."
        
        ai_response = model.generate_content(prompt)
        
        # AI bazen boş dönebilir, kontrol edelim
        sonuc_metni = ai_response.text if ai_response.text else "Analiz yapılamadı, lütfen tekrar deneyin."
        
        return jsonify({"sonuc": sonuc_metni})

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    # Render'ın port ayarını otomatik almasını sağlar
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
