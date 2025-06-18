from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

# ✅ Replace with your real token and phone number ID
ACCESS_TOKEN = "EAAR2slrEDccBO8MTva7RKiVLTvEuszpRQYzpHcBUPPki996mS9l1vCUGupn6vpYe2Ys8ZC7m8zbsVeHNnLxwjZAgyvU7ynI5MRQHL7XGhfTMV4undXZAgAl4wjL8lLNdNcKPo0ZBhMdZCin1qhZAsAXoHu8U5K27j1QZBXs4FzPRdnyTejA1BsrD8W6Sa77oYWUSfwlabnglEbw3MXOqfGzjNpaQid5DNFdyy6eogxzlIKMHTJqg6oZD"
PHONE_NUMBER_ID = "657991800734493"
API_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
VERIFY_TOKEN = "hello"

# ✅ Store messages for debugging/demo
messages = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send():
    data = request.json
    phone_number = data.get("phone_number")
    text = data.get("text")

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": text}
    }

    r = requests.post(API_URL, json=payload, headers=headers)
    print(f"API response: {r.text}")

    messages.append({"from": "me", "text": text})
    return jsonify({"status": "sent"})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFIED!")
            return challenge, 200
        else:
            return "Verification failed", 403

    elif request.method == "POST":
        data = request.json
        print(f"Webhook received: {data}")

        try:
            message = data['entry'][0]['changes'][0]['value']['messages'][0]
            text = message['text']['body']
            messages.append({"from": "them", "text": text})
        except Exception as e:
            print(f"Webhook parse error: {e}")

        return "OK", 200

@app.route("/messages")
def get_messages():
    return jsonify(messages)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
