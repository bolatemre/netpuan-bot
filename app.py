try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        # İlk deneme: Güçlü model (70B)
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [
                {"role": "system", "content": system_msg + "\nJSON format: {'ozet': '...', 'puan': 0.0, 'olumlu': 0, 'kargo': 0, 'olumsuz': 0, 'platform': '...', 'urun_adi': '...', 'istatistik_raporu': '...', 'en_sik_sikayet': '...'}"},
                {"role": "user", "content": user_msg}
            ],
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=20)
        res_data = res.json()

        # Eğer 'choices' gelmediyse (Limit dolduysa) yedek modele geç
        if 'choices' not in res_data:
            print("70B Limiti doldu, 8B'ye geçiliyor...")
            payload["model"] = "llama-3.1-8b-instant"
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
            res_data = res.json()

        ai_data = json.loads(res_data['choices'][0]['message']['content'])
        return jsonify(ai_data)

    except Exception as e:
        print(f"Sistem Hatası: {str(e)}")
        return jsonify({"hata": "AI şu an çok yoğun, lütfen az sonra tekrar deneyin."}), 500
