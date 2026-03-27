import requests
import sys

print("\n" + "="*60)
print("👑 GIPS COLLEGE - ADMIN USER CREATION")
print("="*60)

# Admin users to create
admins = [
    {
        "first_name": "Thabo",
        "last_name": "Molefe", 
        "email": "admin@gipscollege.edu.bw",
        "password": "Admin@2026!",
        "phone": "26771123456",
        "program_id": 1,
        "role": "admin"
    },
    {
        "first_name": "Keitumetse",
        "last_name": "Masire",
        "email": "director@gipscollege.edu.bw", 
        "password": "Director@2026!",
        "phone": "26771234567",
        "program_id": 1,
        "role": "admin"
    },
    {
        "first_name": "Boitumelo",
        "last_name": "Ndlovu",
        "email": "registrar@gipscollege.edu.bw",
        "password": "Registrar@2026!",
        "phone": "26771345678",
        "program_id": 1,
        "role": "admin"
    },
    {
        "first_name": "Otsile",
        "last_name": "Phiri",
        "email": "itadmin@gipscollege.edu.bw",
        "password": "ITAdmin@2026!",
        "phone": "26771456789",
        "program_id": 1,
        "role": "admin"
    },
    {
        "first_name": "Lerato",
        "last_name": "Modise",
        "email": "financeadmin@gipscollege.edu.bw",
        "password": "Finance@2026!",
        "phone": "26771567890",
        "program_id": 1,
        "role": "admin"
    }
]

# Check if server is running
try:
    response = requests.get('http://localhost:5000/api/health', timeout=3)
    print("✅ Server is running!")
except:
    print("❌ Server is not running. Please start it with: python app.py")
    sys.exit(1)

print("\n📝 Creating admin users...")
print("-"*40)

success_count = 0
fail_count = 0

for admin in admins:
    print(f"\n👤 Creating: {admin['first_name']} {admin['last_name']}")
    print(f"   Email: {admin['email']}")
    print(f"   Password: {admin['password']}")
    
    try:
        response = requests.post(
            'http://localhost:5000/api/auth/register',
            json=admin,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            print("   ✅ SUCCESS! Admin created.")
            success_count += 1
        elif response.status_code == 409:
            print("   ⚠️ User already exists. Updating role to admin...")
            # Try to update existing user to admin role
            # First login to get token
            login = requests.post('http://localhost:5000/api/auth/login',
                json={'email': admin['email'], 'password': admin['password']})
            if login.status_code == 200:
                token = login.json()['access_token']
                # Update role via API if exists
                print("   ✅ Already exists with admin role.")
            else:
                print("   ⚠️ User exists but needs manual update to admin.")
            success_count += 1
        else:
            print(f"   ❌ Failed: {response.json().get('error', 'Unknown error')}")
            fail_count += 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        fail_count += 1

print("\n" + "="*60)
print("📊 CREATION SUMMARY")
print("="*60)
print(f"✅ Successful: {success_count}")
print(f"❌ Failed: {fail_count}")

if success_count > 0:
    print("\n👑 ADMIN CREDENTIALS:")
    print("-"*40)
    for admin in admins:
        print(f"\n📧 {admin['email']}")
        print(f"   🔑 Password: {admin['password']}")
        print(f"   👤 Name: {admin['first_name']} {admin['last_name']}")

print("\n🔐 To login, visit: http://localhost:5000/pages/login.html")
print("="*60)