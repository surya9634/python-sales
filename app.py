from flask import Flask, redirect, request, session
import requests

app = Flask(__name__)
app.secret_key = "hello"  # ✅ CHANGE this to something random and secret

# ======== APP CONFIG ========
FB_APP_ID = "2101110903689615"
FB_APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
VERIFY_TOKEN = "hello"  # ✅ same in FB Developer webhook config
REDIRECT_URI = "https://python-sales.onrender.com/callback"  # ✅ your Render URL

# ======== OAUTH STEP 1 ========
@app.route("/")
def login():
    fb_auth_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth"
        f"?client_id={FB_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=pages_show_list,instagram_basic,pages_manage_metadata,"
        f"pages_read_engagement,pages_manage_engagement"
    )
    return redirect(fb_auth_url)

# ======== OAUTH STEP 2 ========
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: Missing code parameter"

    # 1️⃣ Exchange code for short-lived token
    token_url = (
        f"https://graph.facebook.com/v18.0/oauth/access_token"
        f"?client_id={FB_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&client_secret={FB_APP_SECRET}"
        f"&code={code}"
    )
    res = requests.get(token_url).json()
    short_token = res.get("access_token")
    if not short_token:
        return f"Error: Couldn't get short-lived token. Response: {res}"

    # 2️⃣ Exchange for long-lived token
    long_token_url = (
        f"https://graph.facebook.com/v18.0/oauth/access_token"
        f"?grant_type=fb_exchange_token"
        f"&client_id={FB_APP_ID}"
        f"&client_secret={FB_APP_SECRET}"
        f"&fb_exchange_token={short_token}"
    )
    long_res = requests.get(long_token_url).json()
    long_token = long_res.get("access_token")
    if not long_token:
        return f"Error: Couldn't get long-lived token. Response: {long_res}"

    # 3️⃣ Get user's Pages
    pages_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={long_token}"
    pages_res = requests.get(pages_url).json()
    pages = pages_res.get("data", [])
    if not pages:
        return f"Error: No Pages found. Response: {pages_res}"

    # 4️⃣ Use first Page (or you can loop for all)
    page = pages[0]
    page_id = page['id']
    page_token = page['access_token']

    # 5️⃣ Check if IG is connected to Page
    ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={page_token}"
    ig_res = requests.get(ig_url).json()
    ig_id = ig_res.get("instagram_business_account", {}).get("id")

    if not ig_id:
        link_url = f"https://www.facebook.com/{page_id}/settings/?tab=instagram"
        return f"""
        <h3>⚠️ Instagram not connected!</h3>
        <p>Please connect your Instagram Business Account to your Page:</p>
        <a href="{link_url}" target="_blank">👉 Click to link Instagram</a>
        """

    # ✅ Store in session (or DB in real app)
    session['page_id'] = page_id
    session['page_token'] = page_token
    session['ig_id'] = ig_id

    return f"""
    <h3>✅ Success!</h3>
    <p>Page ID: {page_id}</p>
    <p>Instagram Business ID: {ig_id}</p>
    <p>Ready for automation. You can close this window.</p>
    """

# ======== WEBHOOK VERIFICATION ========
@app.route("/webhook", methods=['GET'])
def verify_webhook():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Verification failed", 403

# ======== WEBHOOK EVENT LISTENER ========
@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.json
    print("🔔 New webhook event:", data)

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") == "feed" and value.get("item") == "comment":
                comment_id = value["comment_id"]
                print(f"New comment ID: {comment_id}")

                # ✅ Example: auto DM logic (replace with your real DM API)
                page_token = session.get('page_token')
                ig_id = session.get('ig_id')

                # Here you would send an IG DM or reply
                # For example, you could call the IG Messaging API
                print(f"Would reply to comment {comment_id} using IG ID {ig_id}")

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
