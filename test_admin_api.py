import requests
import json
import time

print("="*60)
print("ADMIN LOGIN & API TEST")
print("="*60)

# Test login
print("\n[1] Testing Login...")
login_response = requests.post(
    'http://localhost:5000/api/auth/login',
    json={'email': 'admin@gipscollege.edu.bw', 'password': 'Admin@2026!'},
    timeout=5
)

print(f"   Status: {login_response.status_code}")

if login_response.status_code == 200:
    data = login_response.json()
    token = data.get('access_token')
    print(f"   ✅ Login successful!")
    print(f"   Token received: {token[:50]}...")
    
    # Test admin stats with token
    print("\n[2] Testing Admin Stats with Token...")
    stats_response = requests.get(
        'http://localhost:5000/api/admin/stats',
        headers={'Authorization': f'Bearer {token}'},
        timeout=5
    )
    print(f"   Status: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        print(f"   ✅ Admin stats working!")
        stats_data = stats_response.json()
        print(f"   Total Students: {stats_data.get('total_students', 0)}")
        print(f"   Total Programs: {stats_data.get('total_programs', 0)}")
    elif stats_response.status_code == 401:
        print(f"   ❌ Token invalid or expired!")
    elif stats_response.status_code == 403:
        print(f"   ❌ Access denied - not admin!")
    else:
        print(f"   ⚠️ Unexpected status: {stats_response.status_code}")
        print(f"   Response: {stats_response.text[:200]}")
else:
    print(f"   ❌ Login failed!")
    print(f"   Response: {login_response.text}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
