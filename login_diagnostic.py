import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'backend'))

print("="*70)
print("LOGIN DIAGNOSTIC - Checking Database Users and Authentication")
print("="*70)

# Step 1: Check database connection
print("\n[1] CHECKING DATABASE CONNECTION...")
try:
    import pymysql
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='Admin',
        port=3306
    )
    print("   ✓ MySQL connection successful!")
    conn.close()
except Exception as e:
    print(f"   ✗ MySQL connection failed: {e}")
    print("   Please ensure MySQL is running with password 'Admin'")

# Step 2: Check if Flask app can connect
print("\n[2] CHECKING FLASK DATABASE CONNECTION...")
from app import create_app
from models import db, User, Student

app = create_app()
with app.app_context():
    try:
        result = db.session.execute('SELECT 1').scalar()
        print(f"   ✓ Flask database connection successful! (Test: {result})")
    except Exception as e:
        print(f"   ✗ Flask database connection failed: {e}")

# Step 3: List all users
print("\n[3] LISTING ALL USERS IN DATABASE...")
with app.app_context():
    users = User.query.all()
    if not users:
        print("   ✗ NO USERS FOUND IN DATABASE!")
        print("   Run: python create_admin_users.py")
    else:
        print(f"   Total users found: {len(users)}")
        print("   " + "-"*50)
        for user in users:
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Role: {user.role}")
            print(f"   Active: {user.is_active}")
            print(f"   Password Hash: {user.password_hash[:50]}..." if user.password_hash else "   Password Hash: None")
            print("   " + "-"*50)

# Step 4: Test password verification for admin
print("\n[4] TESTING PASSWORD VERIFICATION...")
with app.app_context():
    admin_emails = ['admin@gipscollege.edu.bw', 'director@gipscollege.edu.bw', 'registrar@gipscollege.edu.bw']
    test_password = 'Admin@2026!'
    
    for email in admin_emails:
        user = User.query.filter_by(email=email).first()
        if user:
            try:
                is_valid = user.check_password(test_password)
                print(f"   {email}:")
                print(f"      Password '{test_password}' valid: {is_valid}")
                if not is_valid:
                    print(f"      Password hash: {user.password_hash[:80]}...")
            except Exception as e:
                print(f"      Error checking password: {e}")
        else:
            print(f"   {email}: User not found")

# Step 5: Check if admin users exist, if not, create them
print("\n[5] CHECKING ADMIN USERS...")
with app.app_context():
    admin_count = User.query.filter(User.role.in_(['admin', 'administrator'])).count()
    if admin_count == 0:
        print("   ⚠️ No admin users found! Creating them now...")
        from werkzeug.security import generate_password_hash
        
        admin_list = [
            {'username': 'admin', 'email': 'admin@gipscollege.edu.bw', 'password': 'Admin@2026!', 'first_name': 'System', 'last_name': 'Administrator'},
            {'username': 'director', 'email': 'director@gipscollege.edu.bw', 'password': 'Director@2026!', 'first_name': 'Keitumetse', 'last_name': 'Masire'},
            {'username': 'registrar', 'email': 'registrar@gipscollege.edu.bw', 'password': 'Registrar@2026!', 'first_name': 'Boitumelo', 'last_name': 'Ndlovu'},
            {'username': 'itadmin', 'email': 'itadmin@gipscollege.edu.bw', 'password': 'ITAdmin@2026!', 'first_name': 'Otsile', 'last_name': 'Phiri'},
        ]
        
        for admin_data in admin_list:
            existing = User.query.filter_by(email=admin_data['email']).first()
            if not existing:
                new_user = User(
                    username=admin_data['username'],
                    email=admin_data['email'],
                    password_hash=generate_password_hash(admin_data['password']),
                    role='admin',
                    is_active=True,
                    is_verified=True
                )
                db.session.add(new_user)
                db.session.flush()
                
                # Create student record for admin
                new_student = Student(
                    user_id=new_user.id,
                    student_number=f"ADMIN-{admin_data['username'].upper()}",
                    first_name=admin_data['first_name'],
                    last_name=admin_data['last_name'],
                    email=admin_data['email'],
                    is_active=True
                )
                db.session.add(new_student)
                print(f"   ✓ Created: {admin_data['email']} with password: {admin_data['password']}")
        
        db.session.commit()
        print("   ✓ Admin users created successfully!")
    else:
        print(f"   ✓ Found {admin_count} admin users")

# Step 6: Test login via API
print("\n[6] TESTING LOGIN VIA API...")
import requests

login_tests = [
    {'email': 'admin@gipscollege.edu.bw', 'password': 'Admin@2026!'},
    {'email': 'director@gipscollege.edu.bw', 'password': 'Director@2026!'},
    {'email': 'registrar@gipscollege.edu.bw', 'password': 'Registrar@2026!'},
]

for test in login_tests:
    try:
        response = requests.post(
            'http://localhost:5000/api/auth/login',
            json=test,
            timeout=5
        )
        print(f"   {test['email']}:")
        print(f"      Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"      ✓ Login successful! Role: {data.get('user', {}).get('role')}")
        else:
            print(f"      ✗ Login failed: {response.json().get('error', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        print(f"   ✗ Cannot connect to server at http://localhost:5000")
        print("   Please make sure Flask is running: python app.py")
    except Exception as e:
        print(f"   ✗ Error: {e}")

# Step 7: Check if Flask server is running
print("\n[7] CHECKING FLASK SERVER STATUS...")
try:
    response = requests.get('http://localhost:5000/api/health', timeout=3)
    print(f"   ✓ Server is running (Status: {response.status_code})")
    if response.status_code == 200:
        data = response.json()
        print(f"   Database status: {data.get('database', 'unknown')}")
except:
    print("   ✗ Flask server is NOT running!")
    print("   Please start it: python app.py")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
print("\nRECOMMENDED ACTIONS:")
print("1. If no users found: Run 'python create_admin_users.py'")
print("2. If server not running: Run 'python app.py' in another terminal")
print("3. If password verification fails: Password hash may be corrupted")
print("4. Use credentials: admin@gipscollege.edu.bw / Admin@2026!")
