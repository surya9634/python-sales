from flask import Flask, redirect, request, session
import requests
import os

app = Flask(__name__)
app.secret_key = "hello"  # ✅ CHANGE this to something random and secret

# ======== APP CONFIG ========
FB_APP_ID = "2101110903689615"
FB_APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
VERIFY_TOKEN = "hello"  # ✅ same in FB Developer webhook config
REDIRECT_URI = "https://python-sales.onrender.com/callback"  # ✅ your Render URL

# Instagram-only permissions
SCOPES = "instagram_basic,instagram_manage_comments,instagram_manage_messages"

@app.route("/")
def home():
    return f'<a href="/login">Connect your Instagram</a>'

@app.route("/login")
def login():
    auth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code, auth failed"

    # Exchange code for short-lived token
    token_url = (
        f"https://graph.facebook.com/v19.0/oauth/access_token?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}&client_secret={FB_APP_SECRET}&code={code}"
    )
    token_data = requests.get(token_url).json()
    short_token = token_data.get("access_token")

    # Exchange for long-lived token
    long_token_url = (
        f"https://graph.facebook.com/v19.0/oauth/access_token?"
        f"grant_type=fb_exchange_token&client_id={FB_APP_ID}&client_secret={FB_APP_SECRET}"
        f"&fb_exchange_token={short_token}"
    )
    long_token = requests.get(long_token_url).json().get("access_token")

    # Get IG user id and username
    user_info = requests.get(
        f"https://graph.facebook.com/v19.0/me?fields=id,username&access_token={long_token}"
    ).json()

    # Save to session/db
    session["ig_id"] = user_info.get("id")
    session["username"] = user_info.get("username")
    session["access_token"] = long_token

    return f"""
    ✅ Connected!<br>
    IG ID: {user_info.get('id')}<br>
    Username: {user_info.get('username')}<br>
    <br>
    Now you can handle comments & DMs with this token server-side!
    """

if __name__ == "__main__":
    app.run(debug=True)
