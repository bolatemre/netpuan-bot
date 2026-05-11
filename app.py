import os
from flask import Flask, request, jsonify
import google.generativeai as genai
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Senin verdiğin API Key'i buraya tanımlıyoruz
genai.configure(api_key="AQ.Ab8RN6JaFgLSFGdQ7GPljvVYmL7ukcHSQwyyQWiD_r4zHMNXhQ")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            # İlk 10 yorumu çekiyoruz (Hızlı olması için şimdilik az tuttum)
            comments = page.locator(".comment-text").all_inner_texts()[:10]
            browser.close()
            
            # Gemini'ye gönderiyoruz
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Şu ürün yorumlarını analiz et: {comments}. Bana ŞU FORMATTA cevap ver: SKOR: [10 üzerinden], OZET: [3 cümlelik özet], IYI: [%], KARGO: [%], KOTU: [%]"
            response = model.generate_content(prompt)
            
            return jsonify({"sonuc": response.text})
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)