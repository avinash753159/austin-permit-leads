"""
One-time setup: Sign in with avinash@brimstonepartner.com via Google OAuth.

Run this once:
    python setup_email.py

It will:
1. Open your browser
2. Ask you to sign in with avinash@brimstonepartner.com
3. Save your credentials locally so the app can send emails on your behalf

After this, weekly_email.py and outreach tools can send from your account.
"""
import os
import sys
import pickle

# Check dependencies
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install google-auth google-auth-oauthlib google-api-python-client")
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, 'token_brimstone.pickle')

# Look for any available credentials.json in the gmail_credentials_package
CREDS_LOCATIONS = [
    os.path.join(BASE_DIR, 'credentials_brimstone.json'),
    os.path.join(BASE_DIR, '..', 'gmail_credentials_package', 'credentials.json'),
    os.path.join(BASE_DIR, '..', 'gmail_credentials_package', 'credentials_nexan.json'),
    os.path.join(BASE_DIR, 'credentials.json'),
]

def find_credentials():
    for path in CREDS_LOCATIONS:
        if os.path.exists(path):
            return path
    return None

def main():
    print("=" * 60)
    print("  Brimstone Partner - Email Setup")
    print("  Sign in with: avinash@brimstonepartner.com")
    print("=" * 60)

    # Check for existing token
    if os.path.exists(TOKEN_FILE):
        print(f"\nExisting token found: {TOKEN_FILE}")
        try:
            with open(TOKEN_FILE, 'rb') as f:
                creds = pickle.load(f)
            if creds and creds.valid:
                print("Token is still valid. You're all set!")
                return
            elif creds and creds.expired and creds.refresh_token:
                print("Token expired. Refreshing...")
                creds.refresh(Request())
                with open(TOKEN_FILE, 'wb') as f:
                    pickle.dump(creds, f)
                print("Token refreshed. You're all set!")
                return
        except Exception:
            print("Token is corrupt. Will re-authenticate.")

    # Find credentials file
    creds_file = find_credentials()
    if not creds_file:
        print("\nERROR: No OAuth credentials.json found.")
        print("I need a Google Cloud OAuth client credentials file.")
        print(f"Place it at: {CREDS_LOCATIONS[0]}")
        print("\nTo create one:")
        print("  1. Go to console.cloud.google.com")
        print("  2. Select or create a project")
        print("  3. Enable the Gmail API")
        print("  4. Create OAuth credentials (Desktop app)")
        print("  5. Download the JSON and save it as credentials_brimstone.json")
        print(f"     in {BASE_DIR}")
        return

    print(f"\nUsing credentials from: {creds_file}")
    print(f"\nIMPORTANT: When the browser opens, sign in with:")
    print(f"  avinash@brimstonepartner.com")
    print(f"\nGrant all permissions. Then come back here.\n")
    input("Press Enter to open the browser...")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)

        print(f"\n  Token saved to: {TOKEN_FILE}")
        print(f"\n  You're all set! The app can now send emails as")
        print(f"  avinash@brimstonepartner.com")
        print(f"\n  Next: Run weekly_email.py or the outreach tools.")

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nIf you see 'access_denied', make sure:")
        print("  1. avinash@brimstonepartner.com is added as a test user")
        print("     in your Google Cloud project's OAuth consent screen")
        print("  2. The Gmail API is enabled in your Google Cloud project")

if __name__ == '__main__':
    main()
