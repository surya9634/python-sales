import os
from flask import Flask, request, redirect, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ⚙️ Load env variables
APP_ID = os.getenv('APP_ID')
APP_SECRET = os.getenv('APP_SECRET')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Temporary storage (replace with DB in production)
user_tokens = {}

@app.route('/')
def index():
    oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=pages_show_list,instagram_basic,pages_read_engagement,pages_manage_metadata,instagram_manage_messages,pages_manage_engagement"
    )
    return f'<a href="{oauth_url}">Connect your Instagram Account</a>'

@app.route('/callback')
def callback():
    code = request.args.get('code')

    # 1️⃣ Short-lived token
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    token_params = {
        'client_id': APP_ID,
        'client_secret': APP_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code': code
    }
    token_response = requests.get(token_url, params=token_params).json()
    short_token = token_response.get('access_token')

    if not short_token:
        return f"Error getting short-lived token: {token_response}"

    # 2️⃣ Long-lived token
    long_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    long_params = {
        'grant_type': 'fb_exchange_token',
        'client_id': APP_ID,
        'client_secret': APP_SECRET,
        'fb_exchange_token': short_token
    }
    long_response = requests.get(long_url, params=long_params).json()
    long_token = long_response.get('access_token')

    if not long_token:
        return f"Error getting long-lived token: {long_response}"

    # 3️⃣ Get Pages
    pages_url = "https://graph.facebook.com/v19.0/me/accounts"
    pages_params = {
        'access_token': long_token
    }
    pages_response = requests.get(pages_url, params=pages_params).json()

    if 'data' not in pages_response or not pages_response['data']:
        return f"Error: No Pages found. {pages_response}"

    page = pages_response['data'][0]
    page_id = page['id']
    page_token = page['access_token']

    # 4️⃣ Get Instagram Business Account ID
    page_info_url = f"https://graph.facebook.com/v19.0/{page_id}"
    page_info_params = {
        'fields': 'instagram_business_account',
        'access_token': page_token
    }
    page_info = requests.get(page_info_url, params=page_info_params).json()
    ig_account_id = page_info.get('instagram_business_account', {}).get('id')

    if not ig_account_id:
        return f"Error: No Instagram Business Account linked to this Page. Please connect one in FB Page settings."

    # ✅ Store
    user_tokens['long_token'] = long_token
    user_tokens['page_id'] = page_id
    user_tokens['page_token'] = page_token
    user_tokens['ig_account_id'] = ig_account_id

    return (
        f"<h2>✅ Connected successfully!</h2>"
        f"<p><b>Long-lived Token:</b> {long_token}</p>"
        f"<p><b>Page ID:</b> {page_id}</p>"
        f"<p><b>Page Token:</b> {page_token}</p>"
        f"<p><b>Instagram Business Account ID:</b> {ig_account_id}</p>"
    )

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print('WEBHOOK VERIFIED')
            return challenge, 200
        else:
            return 'Verification failed', 403

    if request.method == 'POST':
        data = request.json
        print("🔔 Webhook received:", data)

        # Example: auto reply to comment via DM (pseudo-code)
        # You'd parse the comment ID, user ID, etc., then call the IG Messaging API.

        return 'EVENT_RECEIVED', 200

if __name__ == '__main__':
    app.run(debug=True)
