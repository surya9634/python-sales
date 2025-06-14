import os
from flask import Flask, request, redirect
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# App credentials & config
APP_ID = os.getenv('APP_ID')
APP_SECRET = os.getenv('APP_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

# In-memory token store (use DB for production!)
user_tokens = {}


@app.route('/')
def index():
    # Redirect user to Instagram OAuth dialog
    oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=instagram_basic,pages_show_list,instagram_manage_messages,instagram_manage_comments,pages_read_engagement"
    )
    return f'<h1>Connect your Instagram</h1><a href="{oauth_url}">Login with Instagram</a>'


@app.route('/callback')
def callback():
    # Step 1: Get short-lived token
    code = request.args.get('code')
    token_url = f"https://graph.facebook.com/v19.0/oauth/access_token"
    token_params = {
        'client_id': APP_ID,
        'client_secret': APP_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code': code
    }
    token_response = requests.get(token_url, params=token_params).json()
    short_token = token_response.get('access_token')

    if not short_token:
        return f"Error getting token: {token_response}"

    # Step 2: Exchange for long-lived token
    long_token_url = f"https://graph.facebook.com/v19.0/oauth/access_token"
    long_params = {
        'grant_type': 'fb_exchange_token',
        'client_id': APP_ID,
        'client_secret': APP_SECRET,
        'fb_exchange_token': short_token
    }
    long_response = requests.get(long_token_url, params=long_params).json()
    long_token = long_response.get('access_token')

    if not long_token:
        return f"Error getting long-lived token: {long_response}"

    # Step 3: Save token (for demo, we just print it)
    # You should store it in a database with the user's info!
    user_tokens['user'] = long_token

    return f"Success! Long-lived token saved.<br>Access Token: {long_token}"


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification handshake with Meta
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print('WEBHOOK VERIFIED')
            return challenge, 200
        else:
            return 'Verification failed', 403

    elif request.method == 'POST':
        # Handle webhook events
        data = request.get_json()
        print("Webhook received:", data)

        # Example: auto-reply to new comment on IG post
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change['field'] == 'comments':
                        comment_id = change['value']['id']
                        comment_text = change['value']['message']
                        print(f"New comment: {comment_text}")

                        # Reply to comment
                        access_token = user_tokens.get('user')
                        if access_token:
                            reply_url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
                            reply_data = {
                                'message': "Thanks for your comment! 💬✨",
                                'access_token': access_token
                            }
                            reply_response = requests.post(reply_url, data=reply_data)
                            print("Reply sent:", reply_response.json())

        except Exception as e:
            print("Error handling webhook:", e)

        return 'EVENT_RECEIVED', 200


if __name__ == '__main__':
    app.run(debug=True)
