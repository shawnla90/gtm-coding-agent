#!/usr/bin/env python3
"""setup_oauth.py - one-time Google OAuth so the builder can read and write your Sheets.

This is the step that "just give the prompt to Claude" skips, and the reason a copied script
fails on the first run. The engine talks to Google Sheets as YOU, over OAuth. You create your
own Google Cloud OAuth client once, consent in the browser, and the token lands at
~/.config/gspread/token.json. After that, build_sheet.py just works.

  python3 setup_oauth.py
  python3 setup_oauth.py --no-browser   # print the consent URL instead of opening a browser
"""
import argparse
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    raise SystemExit("google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib")

CLIENT_SECRET = Path.home() / ".config" / "gspread" / "client_secret.json"
OUT = Path.home() / ".config" / "gspread" / "token.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive",
          "https://www.googleapis.com/auth/presentations"]  # presentations = the Google Slides deck export

SETUP_HELP = f"""Missing {CLIENT_SECRET}

Create your own Google OAuth client once (about 5 minutes), then save the downloaded JSON there:
  1. console.cloud.google.com  ->  create a project (e.g. "market-sheets")
  2. Enable the Google Sheets API: console.cloud.google.com/apis/library/sheets.googleapis.com
  3. Enable the Google Drive API:  console.cloud.google.com/apis/library/drive.googleapis.com
  4. APIs and Services -> OAuth consent screen -> User type = External
     (or Internal if you are on Google Workspace). Add your own email as a test user if asked.
  5. APIs and Services -> Credentials -> Create credentials -> OAuth client ID
     -> Application type = Desktop app -> Create
  6. Download the JSON and save it as {CLIENT_SECRET}
Then re-run:  python3 setup_oauth.py

The token is tied to the Google account you sign in with. Use the account that should own the sheets.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-browser", action="store_true",
                    help="print the consent URL instead of opening a browser")
    args = ap.parse_args()
    if not CLIENT_SECRET.exists():
        sys.exit(SETUP_HELP)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    print(">>> A browser will open. Sign in with the Google account that should own your sheets, click Allow.")
    print(">>> If it warns the app is unverified: Advanced -> continue. It is your own app.")
    creds = flow.run_local_server(
        port=0,
        open_browser=not args.no_browser,
        prompt="consent",
        authorization_prompt_message="CONSENT URL >>> {url}",
        success_message="Connected. Close this tab and return to your terminal.",
    )
    OUT.write_text(creds.to_json())
    OUT.chmod(0o600)
    print(f"\nSaved Google token -> {OUT}")
    print("Done. Now run:  python3 build_sheet.py")


if __name__ == "__main__":
    main()
