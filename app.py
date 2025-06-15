import os
from flask import Flask, redirect, request, jsonify
import requests

app = Flask(__name__)

# === CONFIG ===
APP_ID = "2101110903689615"
APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
REDIRECT_URI = "https://python-sales.onrender.com/callback"  # e.g. your Render domain
SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_engagement",
    "pages_manage_metadata",
    "instagram_basic",
    "instagram_manage_messages",
]

# === In-memory "DB" ===
USERS = {}  # {user_id: {access_token, page_id, ig_id}}

# === ROUTES ===

@app.route("/")
def index():
    oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={','.join(SCOPES)}"
    )
    return f"<h1>Connect your Instagram</h1><a href='{oauth_url}'>Login with Facebook</a>"

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided.", 400

    # 1️⃣ Exchange code for short-lived user token
    token_url = (
        f"https://graph.facebook.com/v19.0/oauth/access_token"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&client_secret={APP_SECRET}"
        f"&code={code}"
    )
    res = requests.get(token_url).json()
    user_token = res.get("access_token")
    if not user_token:
        return f"Error exchanging code: {res}", 400

    # 2️⃣ Get long-lived user token
    ll_url = (
        f"https://graph.facebook.com/v19.0/oauth/access_token"
        f"?grant_type=fb_exchange_token"
        f"&client_id={APP_ID}"
        f"&client_secret={APP_SECRET}"
        f"&fb_exchange_token={user_token}"
    )
    res2 = requests.get(ll_url).json()
    long_token = res2.get("access_token")
    if not long_token:
        return f"Error getting long-lived token: {res2}", 400

    # 3️⃣ Get Pages
    pages_url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={long_token}"
    res3 = requests.get(pages_url).json()
    pages = res3.get("data", [])
    if not pages:
        return f"No pages found: {res3}", 400

    # Take first Page for demo
    page = pages[0]
    page_id = page["id"]
    page_token = page["access_token"]

    # 4️⃣ Get IG Business Account ID
    page_details_url = f"https://graph.facebook.com/v19.0/{page_id}?fields=instagram_business_account&access_token={page_token}"
    res4 = requests.get(page_details_url).json()
    ig_id = res4.get("instagram_business_account", {}).get("id")
    if not ig_id:
        return f"No IG Business Account found: {res4}", 400

    # 5️⃣ Save for later
    USERS[page_id] = {
        "page_token": page_token,
        "ig_id": ig_id,
    }

    return f"""
    <h1>Connected!</h1>
    <p>Page ID: {page_id}</p>
    <p>IG Business ID: {ig_id}</p>
    <p>✅ Now you can use this to get comments & auto reply.</p>
    """

@app.route("/reply_comments/<page_id>")
def reply_comments(page_id):
    creds = USERS.get(page_id)
    if not creds:
        return "Page ID not found.", 404

    page_token = creds["page_token"]
    ig_id = creds["ig_id"]

    # 1️⃣ Get latest media
    media_url = f"https://graph.facebook.com/v19.0/{ig_id}/media?fields=id,caption&access_token={page_token}"
    media = requests.get(media_url).json()
    media_id = media["data"][0]["id"]

    # 2️⃣ Get comments on latest media
    comments_url = f"https://graph.facebook.com/v19.0/{media_id}/comments?access_token={page_token}"
    comments = requests.get(comments_url).json()
    comments_data = comments.get("data", [])

    # 3️⃣ Reply to each comment with a DM (or comment reply)
    results = []
    for comment in comments_data:
        comment_id = comment["id"]

        # Send comment reply
        reply_url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
        reply_res = requests.post(reply_url, data={
            "message": "Thank you for your comment!",
            "access_token": page_token
        }).json()

        results.append(reply_res)

    return jsonify(results)
