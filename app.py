from flask import Flask, redirect, request, session, url_for, jsonify, Response
import requests

app = Flask(__name__)
app.secret_key = "hello"  # <-- Change this to anything random

# ======== APP CONFIG ========
FB_APP_ID = "2101110903689615"
FB_APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
VERIFY_TOKEN = "hello"  # Use the same in FB webhook config

# The redirect URI must match EXACTLY what you set in FB Developer dashboard
REDIRECT_URI = "https://python-sales.onrender.com/callback"

# ======== AUTH ROUTES ========

@app.route('/')
def index():
    return '''
        <h1>Welcome to your Automation App!</h1>
        <a href="/login">Login with Facebook & Instagram</a>
    '''

@app.route('/login')
def login():
    fb_auth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={FB_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=pages_show_list,pages_manage_posts,pages_messaging,instagram_basic,instagram_manage_messages"
    )
    return redirect(fb_auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "No code provided", 400

    # Exchange code for access token
    token_url = (
        f"https://graph.facebook.com/v19.0/oauth/access_token?"
        f"client_id={FB_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&client_secret={FB_APP_SECRET}"
        f"&code={code}"
    )
    token_response = requests.get(token_url).json()
    access_token = token_response.get("access_token")

    if not access_token:
        return f"Error getting access token: {token_response}", 400

    session["fb_access_token"] = access_token

    # Get user's pages
    pages_url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}"
    pages_response = requests.get(pages_url).json()
    pages_data = pages_response.get("data", [])

    return jsonify({
        "access_token": access_token,
        "pages": pages_data
    })

# ======== WEBHOOK ROUTE ========

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFIED")
            return Response(challenge, status=200)
        else:
            return Response("Verification failed", status=403)

    elif request.method == 'POST':
        data = request.json
        print(f"Webhook received: {data}")
        # TODO: Process messages/comments here
        return Response("EVENT_RECEIVED", status=200)

# ======== LOGOUT ========

@app.route('/logout')
def logout():
    session.pop("fb_access_token", None)
    return redirect('/')

# ======== MAIN ========

if __name__ == '__main__':
    app.run(debug=True)
