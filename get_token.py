import requests
import webbrowser
import http.server
import socketserver
import urllib.parse
import json
import base64
import secrets
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
CLIENT_ID = os.getenv("EVE_CLIENT_ID")
CLIENT_SECRET = os.getenv("EVE_CLIENT_SECRET")
# Must match your registered callback
CALLBACK_URL = "http://localhost:8080/callback"
SCOPES = "esi-killmails.read_killmails.v1"  # Scope needed for killmail access

# Check if credentials are loaded
if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: Missing credentials in .env file")
    print("Please create a .env file with EVE_CLIENT_ID and EVE_CLIENT_SECRET")
    exit(1)

# Generate PKCE challenge (for enhanced security)
code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(
    code_verifier.encode()).digest()).decode().rstrip('=')

# Server to capture the callback


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        if self.path.startswith('/callback'):
            query_components = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query)
            if 'code' in query_components:
                self.server.authorization_code = query_components['code'][0]
                self.wfile.write(
                    b"Authorization successful! You can close this window now.")
            else:
                self.wfile.write(b"Authorization failed. Please try again.")
        else:
            self.wfile.write(b"Invalid callback path.")

    def log_message(self, format, *args):
        # Suppress server logs
        return


def get_access_token():
    # 1. Start the local server to catch the callback
    httpd = socketserver.TCPServer(("", 8080), CallbackHandler)
    httpd.authorization_code = None
    print("Starting server at http://localhost:8080")

    # 2. Generate the authorization URL and open browser
    auth_url = (
        "https://login.eveonline.com/v2/oauth/authorize/"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={CALLBACK_URL}"
        f"&scope={SCOPES}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
        # You can generate a random state string for extra security
        f"&state=unique-state-string"
    )

    print(f"Opening browser for EVE Online authorization...")
    webbrowser.open(auth_url)

    # 3. Wait for the callback
    print("Waiting for authorization...")
    while httpd.authorization_code is None:
        httpd.handle_request()

    authorization_code = httpd.authorization_code
    print("Authorization code received!")

    # 4. Exchange the authorization code for an access token
    token_url = "https://login.eveonline.com/v2/oauth/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com"
    }
    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code_verifier": code_verifier,
        "redirect_uri": CALLBACK_URL
    }

    response = requests.post(token_url, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in')

        print(f"Access token obtained! Expires in {expires_in} seconds")
        print(f"Access token: {access_token}")

        # Get the character info using the JWT
        jwt_parts = token_data['access_token'].split('.')
        if len(jwt_parts) >= 2:
            # Pad the base64 string properly
            padding = '=' * (4 - len(jwt_parts[1]) % 4)
            jwt_payload = base64.b64decode(jwt_parts[1] + padding)
            character_info = json.loads(jwt_payload)
            character_name = character_info.get('name', 'Unknown')
            character_id = character_info.get('sub', '').split(':')[-1]

            print(f"\nCharacter Name: {character_name}")
            print(f"Character ID: {character_id}")

            # Save tokens to file
            with open('eve_tokens.json', 'w') as f:
                json.dump({
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_in': expires_in,
                    'character_id': character_id,
                    'character_name': character_name
                }, f, indent=2)
            print("\nTokens saved to eve_tokens.json")

            return access_token, character_id

        return access_token, None
    else:
        print(f"Error obtaining token: {response.status_code}")
        print(response.text)
        return None, None


if __name__ == "__main__":
    access_token, character_id = get_access_token()
    if access_token:
        print("\nYou can now use this token with the ship loss tracker script:")
        print(f"python eve_last_loss.py {access_token} {character_id}")
