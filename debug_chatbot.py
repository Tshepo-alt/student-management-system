#!/usr/bin/env python3
"""
Debug script for chatbot "session expired" issue.
Tests login, token refresh, and chatbot API calls.
"""

import requests
import json
import sys
import time
from datetime import datetime
import jwt  # PyJWT library - install with: pip install PyJWT

BASE_URL = "http://localhost:5000"  # Change if your Flask runs on different port/host

def print_section(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def decode_jwt(token):
    """Decode JWT without verification to see payload and expiration."""
    try:
        # Decode without verifying signature (just to see claims)
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        return {"error": str(e)}

def login(email, password):
    """Authenticate and return tokens."""
    print_section("LOGIN")
    print(f"Attempting login with email: {email}")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        print(f"Status code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            print("✅ Login successful")
            return access_token, refresh_token, data
        else:
            print(f"❌ Login failed: {resp.text}")
            return None, None, None
    except Exception as e:
        print(f"❌ Exception during login: {e}")
        return None, None, None

def test_chatbot(access_token, message="Hello, can you help me?"):
    """Send a message to the chatbot endpoint."""
    print_section("CHATBOT API CALL")
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"message": message}
    try:
        resp = requests.post(f"{BASE_URL}/api/chatbot/message", json=payload, headers=headers)
        print(f"Status code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Chatbot response: {data.get('response', 'No response field')[:200]}...")
            return True, data
        else:
            print(f"❌ Chatbot error: {resp.text}")
            return False, resp
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, None

def refresh_token(refresh_token):
    """Try to refresh the access token."""
    print_section("REFRESH TOKEN")
    headers = {"Authorization": f"Bearer {refresh_token}"}
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/refresh", headers=headers)
        print(f"Status code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            new_access_token = data.get('access_token')
            print("✅ Token refreshed successfully")
            return new_access_token
        else:
            print(f"❌ Refresh failed: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def inspect_token(token, name="Access Token"):
    """Decode and print token info."""
    print_section(f"INSPECT {name}")
    if not token:
        print("Token is None")
        return
    decoded = decode_jwt(token)
    print(f"Decoded payload (without verification):")
    print(json.dumps(decoded, indent=2))
    if 'exp' in decoded:
        exp_timestamp = decoded['exp']
        exp_dt = datetime.fromtimestamp(exp_timestamp)
        now = datetime.now()
        print(f"Expires at: {exp_dt}")
        print(f"Remaining time: {exp_dt - now}")
    else:
        print("No 'exp' claim found")

def main():
    print("🔍 Chatbot Session Expiry Debug Tool")
    print("Make sure your Flask server is running on", BASE_URL)
    print("Enter student credentials (or admin) that have access to chatbot.\n")
    
    email = input("Email / Username: ").strip()
    password = input("Password: ").strip()
    
    if not email or not password:
        print("❌ Email and password required.")
        return
    
    # Step 1: Login
    access_token, refresh_token, login_data = login(email, password)
    if not access_token:
        print("Aborting: unable to login.")
        return
    
    # Inspect access token expiry
    inspect_token(access_token, "Access Token")
    
    # Step 2: Test chatbot immediately (should work)
    success, result = test_chatbot(access_token)
    if not success:
        print("Chatbot failed even with fresh token. Check backend logs.")
        # Optionally check refresh token
        if refresh_token:
            inspect_token(refresh_token, "Refresh Token")
        return
    
    # Step 3: Simulate waiting for token to expire (optional)
    print("\n" + "="*60)
    print(" Do you want to simulate token expiration?")
    print(" If your tokens expire quickly, we can wait for a few seconds.")
    choice = input("Wait for expiration? (y/n): ").strip().lower()
    if choice == 'y':
        try:
            wait_sec = int(input("How many seconds to wait? (e.g., 30): "))
        except:
            wait_sec = 30
        print(f"Waiting {wait_sec} seconds... (press Ctrl+C to skip)")
        for i in range(wait_sec):
            time.sleep(1)
            print(f"\rWaiting... {i+1}/{wait_sec}", end="")
        print("\nResuming...")
    
    # Step 4: Try chatbot again (may be expired now)
    print_section("TEST CHATBOT AFTER WAIT (if any)")
    success2, result2 = test_chatbot(access_token)
    if not success2:
        print("Chatbot returned 401 as expected after expiration? Let's try refresh.")
        if refresh_token:
            new_access_token = refresh_token(refresh_token)
            if new_access_token:
                print("Retrying chatbot with new access token...")
                success3, result3 = test_chatbot(new_access_token)
                if success3:
                    print("✅ Refresh and retry succeeded!")
                else:
                    print("❌ Still failing after refresh. Check chatbot backend.")
            else:
                print("❌ Refresh token endpoint failed. Check /api/auth/refresh implementation and JWT settings.")
        else:
            print("No refresh token available. Check login response.")
    else:
        print("Chatbot still works after wait. Tokens did not expire or wait was too short.")

if __name__ == "__main__":
    main()