from flask import Flask, request, redirect, session
import requests

app = Flask(__name__)
app.secret_key = "hello"  # <-- Your app secret key

# ======== APP CONFIG ========
FB_APP_ID = "2101110903689615"
FB_APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
VERIFY_TOKEN = "hello"  # Must match what you enter in FB webhook config
REDIRECT_URI = "https://python-sales.onrender.com/callback"

# ======== HOME PAGE ========
@app.route('/')
def index():
    return '<h2>Welcome! <a href="/login">Login with Facebook</a></h2>'

# ======== STEP 1: Login URL ========
@app.route('/login')
def login():
    fb_auth_url = (
        f"https://www.facebook.com/v17.0/dialog/oauth?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}&scope=pages_show_list,pages_messaging"
    )
    return redirect(fb_auth_url)

# ======== STEP 2: OAuth Callback ========
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error: No code returned."

    # Exchange code for access token
    token_url = (
        f"https://graph.facebook.com/v17.0/oauth/access_token?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}&client_secret={FB_APP_SECRET}&code={code}"
    )
    response = requests.get(token_url).json()
    access_token = response.get("access_token")

    if not access_token:
        return f"Error getting access token: {response}"

    # Save token to session
    session["fb_access_token"] = access_token

    return f"Login successful! Access Token: {access_token}"

# ======== STEP 3: Webhook Verification & Event Handling ========
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("[Webhook] Verified successfully!")
            return challenge, 200
        else:
            print("[Webhook] Verification failed.")
            return "Verification failed", 403

    elif request.method == 'POST':
        data = request.json
        print("[Webhook] Received event:", data)
        return "EVENT_RECEIVED", 200

    else:
        return "Method not allowed", 405

# ======== RUN ========
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
