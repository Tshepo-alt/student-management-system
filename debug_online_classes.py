#!/usr/bin/env python3
import requests
import json

print("Script started.")  # immediate confirmation

BASE_URL = "https://student-management-system-lks1.onrender.com"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
START_URL = f"{BASE_URL}/api/classes/course/1/start"

# Lecturer credentials – adjust if needed
EMAIL = "lecturer@example.com"
PASSWORD = "Admin123!"

print("1. Logging in...")
resp = requests.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
print(f"   Login status: {resp.status_code}")

if resp.status_code != 200:
    print("   Error:", resp.text)
    exit(1)

data = resp.json()
token = data.get("access_token")
print(f"   Token obtained (first 20 chars): {token[:20]}...")

print("2. Starting meeting for course 1...")
headers = {"Authorization": f"Bearer {token}"}
resp2 = requests.post(START_URL, json={"platform": "google_meet"}, headers=headers)
print(f"   Start meeting status: {resp2.status_code}")
print("   Response body:")
try:
    print(json.dumps(resp2.json(), indent=2))
except:
    print(resp2.text)

print("Done.")