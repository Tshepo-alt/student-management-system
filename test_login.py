import requests
import json

print("="*60)
print("TESTING LOGIN ENDPOINT")
print("="*60)

# Test with admin credentials
response = requests.post(
    'http://localhost:5000/api/auth/login',
    json={'email': 'admin@gipscollege.edu.bw', 'password': 'Admin@2026!'},
    headers={'Content-Type': 'application/json'}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
