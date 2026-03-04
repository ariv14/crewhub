#!/usr/bin/env python3
"""Open a browser for Firebase Google login and capture the auth token.

Uses Playwright in headed (visible) mode so Google doesn't block the login.
After successful login, extracts the Firebase ID token and saves it to auth.txt.

Usage:
    python scripts/get_firebase_token.py
"""

import json
import time
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Install playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

# The frontend that uses Firebase auth
FRONTEND_URL = "https://aidigitalcrew.com"
# Fallback: try the staging direct
STAGING_URL = "https://arimatch1-crewhub-staging.hf.space"

OUTPUT_FILE = "auth.txt"


def main():
    with sync_playwright() as p:
        # Use headed mode (visible browser) — Google blocks headless
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"\n  Opening browser to {FRONTEND_URL}")
        print("  Please log in with your Google account.")
        print("  The token will be captured automatically.\n")

        page.goto(FRONTEND_URL)

        # Wait for the user to complete login — look for the auth token
        # in localStorage or in network requests
        token = None

        print("  Waiting for login... (monitoring localStorage and network)")

        for attempt in range(120):  # 2 minutes max
            time.sleep(1)

            # Check localStorage for Firebase auth token
            try:
                result = page.evaluate("""() => {
                    // Check for Firebase auth user in localStorage
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        const val = localStorage.getItem(key);
                        if (key.includes('firebase:authUser') || key === 'auth_token') {
                            try {
                                const parsed = JSON.parse(val);
                                // Firebase authUser object
                                if (parsed.stsTokenManager && parsed.stsTokenManager.accessToken) {
                                    return parsed.stsTokenManager.accessToken;
                                }
                                // Direct token
                                if (typeof parsed === 'string' && parsed.startsWith('eyJ')) {
                                    return parsed;
                                }
                            } catch(e) {
                                if (val && val.startsWith('eyJ')) {
                                    return val;
                                }
                            }
                        }
                    }
                    return null;
                }""")

                if result:
                    token = result
                    break
            except Exception:
                pass  # Page might be navigating

            if attempt % 10 == 0 and attempt > 0:
                print(f"  Still waiting... ({attempt}s)")

        if token:
            with open(OUTPUT_FILE, "w") as f:
                f.write(token)
            print(f"\n  Token saved to {OUTPUT_FILE}")
            print(f"  Token preview: {token[:50]}...")
        else:
            print("\n  Failed to capture token automatically.")
            print("  Try copying it manually from DevTools > Application > Local Storage")

        print("\n  Closing browser in 5 seconds...")
        time.sleep(5)
        browser.close()


if __name__ == "__main__":
    main()
