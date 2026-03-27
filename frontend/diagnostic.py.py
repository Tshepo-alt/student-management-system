import requests
import json

print("=" * 60)
print("🔍 GIPS COLLEGE LOGIN DIAGNOSTIC TOOL")
print("=" * 60)

# Test 1: Check if server is running
print("\n📡 TEST 1: Checking server connection...")
try:
    response = requests.get('http://localhost:5000/api/health', timeout=5)
    print(f"   ✅ Server is running! Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except requests.exceptions.ConnectionError:
    print("   ❌ Server is NOT running! Start your server with: python app.py")
    exit()
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit()

# Test 2: Try to login with demo credentials
print("\n🔐 TEST 2: Testing login with demo credentials...")
test_login = {
    "email": "student@example.com",
    "password": "Student123!"
}

try:
    response = requests.post(
        'http://localhost:5000/api/auth/login',
        json=test_login,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Login SUCCESSFUL!")
        print(f"   Access Token: {data.get('access_token', 'N/A')[:50]}...")
        print(f"   Refresh Token: {data.get('refresh_token', 'N/A')[:50]}...")
        print(f"   User ID: {data.get('user', {}).get('id', 'N/A')}")
        print(f"   User Email: {data.get('user', {}).get('email', 'N/A')}")
        print(f"   User Role: {data.get('user', {}).get('role', 'N/A')}")
        print(f"   User Name: {data.get('user', {}).get('first_name', 'N/A')} {data.get('user', {}).get('last_name', 'N/A')}")
        
        token = data.get('access_token')
    else:
        data = response.json()
        print(f"   ❌ Login FAILED!")
        print(f"   Error Message: {data.get('message', data.get('error', 'Unknown error'))}")
        token = None
except Exception as e:
    print(f"   ❌ Error during login: {e}")
    token = None

# Test 3: Check if user exists in database
print("\n🗄️ TEST 3: Checking users in database...")
try:
    import pymysql
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Admin',
        database='gips_college_db',
        charset='utf8mb4'
    )
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, email, first_name, last_name, role, is_active FROM users LIMIT 5")
        users = cursor.fetchall()
        
        if users:
            print(f"   Found {len(users)} users in database:")
            for user in users:
                print(f"   - ID: {user[0]}, Email: {user[1]}, Name: {user[2]} {user[3]}, Role: {user[4]}, Active: {user[5]}")
        else:
            print("   ⚠️ No users found in database!")
            print("   Register a user first at: http://localhost:5000/pages/register.html")
    
    connection.close()
except ImportError:
    print("   ⚠️ pymysql not installed. Run: pip install pymysql")
except Exception as e:
    print(f"   ⚠️ Could not connect to database: {e}")

# Test 4: Try to access protected endpoint with token
if token:
    print("\n🔒 TEST 4: Testing protected endpoint with token...")
    try:
        response = requests.get(
            'http://localhost:5000/api/students/dashboard',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Protected endpoint ACCESS GRANTED!")
            print(f"   Dashboard data received")
        elif response.status_code == 401:
            print("   ❌ Token INVALID or EXPIRED!")
        elif response.status_code == 404:
            print("   ⚠️ Endpoint not found! Check if /api/students/dashboard exists")
        else:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
else:
    print("\n🔒 TEST 4: Skipping - no token available")

# Summary
print("\n" + "=" * 60)
print("📋 DIAGNOSTIC SUMMARY:")
print("=" * 60)

if token:
    print("✅ Login works from API perspective")
    print("✅ Token is being generated correctly")
    print("\n⚠️ If you see 'Login successful' but not logged in on browser:")
    print("   1. Check browser console (F12) for JavaScript errors")
    print("   2. Check if localStorage is storing the token")
    print("   3. Check if redirect path is correct")
    print("\n👉 To check localStorage in browser:")
    print("   - Open Developer Tools (F12)")
    print("   - Go to Console tab")
    print("   - Type: console.log(localStorage.getItem('access_token'))")
    print("   - Type: console.log(localStorage.getItem('user'))")
else:
    print("❌ Login failed from API")
    print("\nPossible issues:")
    print("   1. User doesn't exist in database")
    print("   2. Wrong credentials")
    print("   3. User account is inactive")
    print("\n👉 Try registering a new user at:")
    print("   http://localhost:5000/pages/register.html")

print("\n" + "=" * 60)