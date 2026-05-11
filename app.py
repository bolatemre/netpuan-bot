import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Groq Anahtarı
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.route('/analiz', methods=['GET'])
def analiz_et():
    url = request.args.get('url')
    if not url: return jsonify({"hata": "Link eksik"}), 400

    try:
        # Test yorumu
        comments = "Ürün harika, kargo çok hızlıydı, kesinlikle tavsiye ederim."

        # Groq API Bağlantısı (Llama 3 modeli ile - Işık hızında)
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "Sen dürüst bir ürün analiz asistanısın. Yorumları 3 kısa cümlede özetle."},
                {"role": "user", "content": f"Şu yorumları analiz et: {comments}"}
            ]
        }
        
        response = requests.post(groq_url, json=payload, headers=headers, timeout=10)
        res_json = response.json()

        if "choices" in res_json:
            ai_text = res_json['choices'][0]['message']['content']
            return jsonify({"sonuc": ai_text})
        else:
            return jsonify({"hata": "Groq hatası", "detay": res_json}), 500

    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
