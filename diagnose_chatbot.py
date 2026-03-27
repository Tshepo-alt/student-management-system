#!/usr/bin/env python3
"""
Chatbot Diagnostic Script
Tests the authentication and chatbot endpoint, including token refresh.
Run this from the project root: python diagnose_chatbot.py
"""

import requests
import json
import sys
from datetime import datetime

# ----------------------------
# Configuration
# ----------------------------
BASE_URL = "http://localhost:5000"   # Change if your server runs on a different port/URL
LOGIN_ENDPOINT = f"{BASE_URL}/api/auth/login"
CHATBOT_ENDPOINT = f"{BASE_URL}/api/chatbot/message"
REFRESH_ENDPOINT = f"{BASE_URL}/api/auth/refresh"

# Test credentials – change these to a valid user in your system
TEST_EMAIL = "student@example.com"   # Replace with a real email
TEST_PASSWORD = "your_password"      # Replace with the real password

# If you want to test with a specific token (from localStorage), uncomment:
# ACCESS_TOKEN = "your_access_token_here"

def print_section(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_login():
    """Test login and return tokens."""
    print_section("1. Testing Login")
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    try:
        response = requests.post(LOGIN_ENDPOINT, json=payload)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            access = data.get('access_token')
            refresh = data.get('refresh_token')
            print(f"✅ Login successful!")
            print(f"Access token: {access[:50]}... (truncated)")
            print(f"Refresh token: {refresh[:50]}... (truncated)")
            return access, refresh
        else:
            print(f"❌ Login failed: {response.status_code}")
            print("Response body:")
            print(json.dumps(response.json(), indent=2))
            return None, None
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}. Is the Flask app running?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None, None

def test_chatbot(access_token, refresh_token):
    """Call chatbot endpoint with given access token. If 401, try to refresh."""
    print_section("2. Testing Chatbot Endpoint with current token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"message": "Hello"}
    try:
        response = requests.post(CHATBOT_ENDPOINT, json=payload, headers=headers)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chatbot responded:")
            print(json.dumps(data, indent=2))
            return True
        elif response.status_code == 401:
            print("⚠️ Token expired or invalid. Attempting refresh...")
            # Try to refresh
            refresh_headers = {"Authorization": f"Bearer {refresh_token}"}
            refresh_resp = requests.post(REFRESH_ENDPOINT, headers=refresh_headers)
            if refresh_resp.status_code == 200:
                new_token = refresh_resp.json().get('access_token')
                print(f"✅ Token refreshed. New token: {new_token[:50]}...")
                # Retry chatbot with new token
                headers["Authorization"] = f"Bearer {new_token}"
                retry_resp = requests.post(CHATBOT_ENDPOINT, json=payload, headers=headers)
                if retry_resp.status_code == 200:
                    print(f"✅ Chatbot responded after refresh:")
                    print(json.dumps(retry_resp.json(), indent=2))
                    return True
                else:
                    print(f"❌ Chatbot still failed after refresh: {retry_resp.status_code}")
                    print(retry_resp.text)
                    return False
            else:
                print(f"❌ Token refresh failed: {refresh_resp.status_code}")
                print(refresh_resp.text)
                return False
        else:
            print(f"❌ Unexpected response from chatbot: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error calling chatbot: {e}")
        return False

def test_with_manual_token():
    """If you have a token from browser, test it directly."""
    print_section("Manual Token Test")
    token = input("Paste your access token (from localStorage): ").strip()
    if not token:
        print("No token provided. Skipping.")
        return
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"message": "Hello"}
    try:
        response = requests.post(CHATBOT_ENDPOINT, json=payload, headers=headers)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Chatbot responded!")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ Failed. Response:")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("\n🔍 Starting Chatbot Diagnostics")
    print(f"Server: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Option 1: Login and test
    access, refresh = test_login()
    if access and refresh:
        test_chatbot(access, refresh)
    else:
        print("\n⚠️ Login failed. You can still test with a manual token.")
        test_with_manual_token()

    # Option 2: If you want to test with a token you already have, uncomment:
    # test_with_manual_token()

    print("\n" + "="*60)
    print(" Diagnostics finished.")
    print("="*60)

if __name__ == "__main__":
    main()