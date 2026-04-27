import requests
import json

BASE_URL = "https://student-management-system-lks1.onrender.com"
LOGIN_URL = f"{BASE_URL}/api/auth/login"

# Your registrar credentials
REGISTRAR_EMAIL = "registrar@gipscollege.edu.bw"
REGISTRAR_PASSWORD = "Admin123!"

# Ask for registration ID
REGISTRATION_ID = input("Enter the registration ID to confirm: ").strip()
if not REGISTRATION_ID.isdigit():
    print("Invalid registration ID. Please enter a number.")
    exit(1)

# Adjust the endpoint pattern if needed
# Common possibilities: /api/admin/registrations/{}/approve, /api/admin/registrations/{}/confirm, etc.
# Try the most likely one first. If you get 404, change the pattern below.
ENDPOINT_PATTERN = "/api/admin/registrations/{}/approve"

CONFIRM_URL = BASE_URL + ENDPOINT_PATTERN.format(REGISTRATION_ID)

def login():
    resp = requests.post(LOGIN_URL, json={"email": REGISTRAR_EMAIL, "password": REGISTRAR_PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} - {resp.text}")
        return None
    data = resp.json()
    token = data.get("access_token")
    if not token:
        print("No access token in response")
        print(data)
        return None
    print("Login successful")
    return token

def confirm_registration(token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"status": "approved"}  # adjust if needed
    print(f"Calling {CONFIRM_URL}")
    resp = requests.post(CONFIRM_URL, json=payload, headers=headers)
    print(f"Response status: {resp.status_code}")
    try:
        print("Response body:")
        print(json.dumps(resp.json(), indent=2))
    except:
        print(resp.text)
    return resp

if __name__ == "__main__":
    token = login()
    if token:
        confirm_registration(token)