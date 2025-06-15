import os
import requests
from flask import Flask, redirect, request, session, jsonify

app = Flask(__name__)
app.secret_key = "hello"

# ======== META API CONFIG ========
FB_APP_ID = "2101110903689615"
FB_APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
VERIFY_TOKEN = "hello"
REDIRECT_URI = "https://python-sales.onrender.com/callback"

# ======== HOME PAGE ========
@app.route("/")
def index():
    fb_login_url = (
        f"https://www.facebook.com/v12.0/dialog/oauth?"
        f"client_id={FB_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=pages_show_list,instagram_basic,pages_manage_metadata,pages_read_engagement"
    )
    return f'''
    <h2>📸 Insta AutoLink Demo</h2>
    <a href="{fb_login_url}">🔗 Connect your Facebook & Instagram</a>
    '''

# ======== OAUTH CALLBACK ========
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided."

    # Exchange code for access token
    token_response = requests.get(
        f"https://graph.facebook.com/v12.0/oauth/access_token",
        params={
            "client_id": FB_APP_ID,
            "redirect_uri": REDIRECT_URI,
            "client_secret": FB_APP_SECRET,
            "code": code,
        },
    ).json()

    user_access_token = token_response.get("access_token")
    if not user_access_token:
        return "Failed to get access token."

    # Get user's pages
    pages_response = requests.get(
        f"https://graph.facebook.com/v12.0/me/accounts",
        params={"access_token": user_access_token}
    ).json()

    if "data" not in pages_response or len(pages_response["data"]) == 0:
        return "No pages found. Please create a Facebook Page first."

    # Pick first Page for demo
    page = pages_response["data"][0]
    page_id = page["id"]
    page_token = page["access_token"]

    # Store in session
    session["page_id"] = page_id
    session["page_token"] = page_token

    # Check if IG is linked
    page_info = requests.get(
        f"https://graph.facebook.com/v12.0/{page_id}",
        params={
            "fields": "instagram_business_account",
            "access_token": page_token
        }
    ).json()

    if "instagram_business_account" in page_info:
        session["ig_id"] = page_info["instagram_business_account"]["id"]
        return redirect("/setup_done")

    # If IG NOT linked → open settings + start polling
    fb_page_settings_url = f"https://www.facebook.com/{page_id}/settings/?tab=instagram"
    return f"""
    <h3>🔗 Your Page is not linked to Instagram yet.</h3>
    <p>Click <a href="{fb_page_settings_url}" target="_blank">HERE to link Instagram</a> — we’ll detect automatically when you finish!</p>
    <p>✅ Please keep this page open.</p>
    <script>
    setInterval(function() {{
        fetch('/check_ig_link').then(res => res.json()).then(data => {{
            if (data.linked) {{
                window.location.href = "/setup_done";
            }}
        }});
    }}, 5000);
    </script>
    """

# ======== POLLING CHECK ========
@app.route("/check_ig_link")
def check_ig_link():
    page_id = session.get("page_id")
    page_token = session.get("page_token")
    if not page_id or not page_token:
        return jsonify({"linked": False})

    page_info = requests.get(
        f"https://graph.facebook.com/v12.0/{page_id}",
        params={
            "fields": "instagram_business_account",
            "access_token": page_token
        }
    ).json()

    if "instagram_business_account" in page_info:
        session["ig_id"] = page_info["instagram_business_account"]["id"]
        return jsonify({"linked": True})
    else:
        return jsonify({"linked": False})

# ======== FINAL SETUP DONE ========
@app.route("/setup_done")
def setup_done():
    return """
    <h2>✅ Instagram is now linked!</h2>
    <p>You can now set up auto comment replies and DMs.</p>
    """

# ======== WEBHOOK VERIFY ========
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Invalid token", 403
    else:
        # Here you handle new comments etc.
        print("Webhook received:", request.json)
        return "ok", 200

# ======== RUN SERVER ========
if __name__ == "__main__":
    app.run(debug=True)
