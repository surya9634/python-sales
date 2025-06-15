import os
from flask import Flask, redirect, request, session
import requests
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this to anything random for sessions

# === HARDCODED CONFIG ===
FB_APP_ID = "2101110903689615"
FB_APP_SECRET = "822f24a839da1b6ebde282d53818cb8f"
FB_REDIRECT_URI = "http://https://python-sales.onrender.com//callback"

FB_SCOPES = "pages_show_list,pages_read_engagement,instagram_basic,public_profile"

# === ROUTES ===

@app.route('/')
def home():
    fb_auth_url = "https://www.facebook.com/v19.0/dialog/oauth?" + urlencode({
        "client_id": FB_APP_ID,
        "redirect_uri": FB_REDIRECT_URI,
        "scope": FB_SCOPES,
        "response_type": "code"
    })
    return f'''
        <h2>FB+IG Connect</h2>
        <a href="{fb_auth_url}">Connect with Facebook</a>
    '''


@app.route('/callback')
def callback():
    # Step 1: Exchange code for short-lived token
    code = request.args.get("code")
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    token_params = {
        "client_id": FB_APP_ID,
        "client_secret": FB_APP_SECRET,
        "redirect_uri": FB_REDIRECT_URI,
        "code": code
    }
    token_response = requests.get(token_url, params=token_params).json()
    short_token = token_response.get("access_token")

    if not short_token:
        return f"Error getting token: {token_response}"

    # Step 2: Exchange for long-lived token
    long_token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    long_params = {
        "grant_type": "fb_exchange_token",
        "client_id": FB_APP_ID,
        "client_secret": FB_APP_SECRET,
        "fb_exchange_token": short_token
    }
    long_response = requests.get(long_token_url, params=long_params).json()
    long_token = long_response.get("access_token")

    if not long_token:
        return f"Error exchanging for long-lived token: {long_response}"

    session['fb_token'] = long_token

    return redirect("/pages")


@app.route('/pages')
def pages():
    token = session.get('fb_token')
    if not token:
        return redirect("/")

    pages_url = f"https://graph.facebook.com/v19.0/me/accounts"
    pages_response = requests.get(pages_url, params={"access_token": token}).json()

    pages_list = pages_response.get("data", [])

    if not pages_list:
        return "No pages found. Please create a Facebook Page first."

    html = "<h3>Select a Page:</h3>"
    for page in pages_list:
        html += f'<p><a href="/check_page?page_id={page["id"]}">{page["name"]}</a></p>'
    return html


@app.route('/check_page')
def check_page():
    token = session.get('fb_token')
    page_id = request.args.get("page_id")

    # Step 4: Get Page access token
    page_url = f"https://graph.facebook.com/v19.0/{page_id}"
    page_info = requests.get(page_url, params={
        "fields": "access_token,name",
        "access_token": token
    }).json()

    page_token = page_info.get("access_token")

    if not page_token:
        return f"Error getting Page token: {page_info}"

    # Step 5: Check if Instagram is linked
    ig_check_url = f"https://graph.facebook.com/v19.0/{page_id}"
    ig_info = requests.get(ig_check_url, params={
        "fields": "instagram_business_account",
        "access_token": page_token
    }).json()

    ig_account = ig_info.get("instagram_business_account")

    if ig_account:
        return f"<h3>✅ Instagram Business Account is connected!</h3><p>ID: {ig_account['id']}</p>"
    else:
        connect_url = f"https://www.facebook.com/{page_id}/settings/?tab=linked_accounts"
        return f'''
            <h3>❌ Instagram Business Account is NOT connected.</h3>
            <p>Please connect it manually:</p>
            <a href="{connect_url}" target="_blank">Connect Instagram to this Page</a>
        '''


@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")


if __name__ == '__main__':
    app.run(debug=True)
