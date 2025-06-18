from flask import Flask, request
import requests

app = Flask(__name__)

# === CONFIG ===
VERIFY_TOKEN = "SurajVerifyToken123"   # you can pick any string, set same in Meta
ACCESS_TOKEN = "EAAR2slrEDccBO8MTva7RKiVLTvEuszpRQYzpHcBUPPKi996mS9l1vCUGupn6vpYe2Ys8ZC7m8zbsVeH"
PHONE_NUMBER_ID = "657991800734493"
GROQ_API_KEY = "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"  # <-- Replace with your real Groq API key
RECIPIENT_PHONE = "919897940269"    # Without '+'

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
            if request.args.get("hub.verify_token") == VERIFY_TOKEN:
                return request.args["hub.challenge"], 200
            return "Verification token mismatch", 403
        return "Hello, Suraj!", 200

    if request.method == "POST":
        data = request.json
        print("Incoming:", data)

        # Extract message text
        messages = data['entry'][0]['changes'][0]['value'].get('messages')
        if messages:
            msg = messages[0]
            phone_number = msg['from']
            user_text = msg['text']['body']

            # Call Groq Llama3
            llama_response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-70b-8192",
                    "messages": [
                        {"role": "user", "content": user_text}
                    ]
                }
            )
            bot_reply = llama_response.json()['choices'][0]['message']['content']

            # Send reply back on WhatsApp
            url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "text": {"body": bot_reply}
            }
            requests.post(url, headers=headers, json=payload)

        return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
