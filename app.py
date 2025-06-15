from flask import Flask, request, redirect, session
import requests
import os

app = Flask(__name__)
app.secret_key = "hello"

FB_APP_ID = "2101110903689615"
FB_APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
VERIFY_TOKEN = "hello"
REDIRECT_URI = "https://python-sales.onrender.com/callback"

# ========== LOGIN ==========
@app.route('/login')
def login():
    fb_login_url = (
        f"https://www.facebook.com/v12.0/dialog/oauth?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}&scope=pages_manage_metadata,pages_read_engagement,pages_show_list,instagram_manage_messages,instagram_manage_comments,instagram_basic,business_management"
    )
    return redirect(fb_login_url)


# ========== OAUTH CALLBACK ==========
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "No code in request", 400

    # Exchange code for short-lived user token
    token_url = (
        f"https://graph.facebook.com/v12.0/oauth/access_token?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}&client_secret={FB_APP_SECRET}&code={code}"
    )
    token_response = requests.get(token_url).json()
    user_access_token = token_response.get("access_token")
    if not user_access_token:
        return f"Error getting user token: {token_response}", 400

    # Exchange for long-lived user token
    long_lived_url = (
        f"https://graph.facebook.com/v12.0/oauth/access_token?"
        f"grant_type=fb_exchange_token&client_id={FB_APP_ID}&client_secret={FB_APP_SECRET}&fb_exchange_token={user_access_token}"
    )
    long_lived_response = requests.get(long_lived_url).json()
    long_lived_token = long_lived_response.get("access_token")
    if not long_lived_token:
        return f"Error getting long-lived token: {long_lived_response}", 400

    session['user_token'] = long_lived_token
    return redirect('/connect')


# ========== CONNECT PAGE + IG ==========
@app.route('/connect')
def connect():
    user_token = session.get('user_token')
    if not user_token:
        return "No user token found", 400

    # Get user's Pages
    pages = requests.get(
        f"https://graph.facebook.com/v12.0/me/accounts",
        params={"access_token": user_token}
    ).json()

    if 'data' not in pages or len(pages['data']) == 0:
        return "No pages found", 400

    page = pages['data'][0]  # first page
    page_id = page['id']
    page_token = page['access_token']

    # Get connected Instagram Business Account
    page_info = requests.get(
        f"https://graph.facebook.com/v12.0/{page_id}?fields=instagram_business_account",
        params={"access_token": page_token}
    ).json()

    ig_account = page_info.get('instagram_business_account')
    if not ig_account:
        return "This Page is not linked to an Instagram account. Please link it in Facebook Page settings.", 400

    ig_id = ig_account['id']

    # Save tokens + IDs to session or DB
    session['page_token'] = page_token
    session['page_id'] = page_id
    session['ig_id'] = ig_id

    return f"Connected Page ID: {page_id}<br>Instagram Account ID: {ig_id}<br>Webhook is ready!"


# ========== WEBHOOK ==========
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # FB verification
        if request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        else:
            return 'Verification failed', 403

    elif request.method == 'POST':
        data = request.get_json()
        print("Webhook event:", data)

        # Example: listen for Instagram comment
        if 'entry' in data:
            for entry in data['entry']:
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    if value.get('field') == 'comments':
                        comment_id = value['id']
                        media_id = value['media']['id']
                        user_id = entry['id']
                        ig_id = session.get('ig_id')
                        page_token = session.get('page_token')

                        if ig_id and page_token:
                            # Send DM reply
                            dm_url = f"https://graph.facebook.com/v12.0/{ig_id}/messages"
                            payload = {
                                "recipient": {"comment_id": comment_id},
                                "message": {"text": "Hello! 👋 Thank you for commenting!"}
                            }
                            resp = requests.post(dm_url, params={"access_token": page_token}, json=payload)
                            print("DM response:", resp.text)

        return 'EVENT_RECEIVED', 200


@app.route('/')
def home():
    return 'Bot server is running. <a href="/login">Login with Facebook</a>'


if __name__ == '__main__':
    app.run(debug=True)
