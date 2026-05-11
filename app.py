import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.route('/analiz', methods=['POST']) # GET yerine POST yapıyoruz, veri büyük gelecek
def analiz_et():
    data = request.json
    raw_comments = data.get('comments', '')
    
    if not raw_comments or len(raw_comments) < 10:
        return jsonify({"hata": "Analiz edilecek yeterli yorum bulunamadı."}), 400

    try:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "Sen bir analizörsün. Gelen yorumları dürüstçe puanla ve JSON formatında dön: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0}"},
                {"role": "user", "content": f"Yorumlar: {raw_comments}"}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post(groq_url, json=payload, headers=headers)
        return jsonify(json.loads(res.json()['choices'][0]['message']['content']))
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == "__main__":
    app.run()
