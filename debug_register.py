# debug_register.py
import sys
import os
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

print("="*60)
print("🔍 DEBUGGING REGISTRATION ERROR")
print("="*60)

# Step 1: Check User model fields
print("\n📋 1. CHECKING USER MODEL FIELDS...")
try:
    from models import User
    print("✅ User model imported successfully")
    print("   User model fields:")
    for column in User.__table__.columns:
        print(f"   - {column.name}: {column.type}")
except Exception as e:
    print(f"❌ Error: {e}")

# Step 2: Check Student model fields
print("\n📋 2. CHECKING STUDENT MODEL FIELDS...")
try:
    from models import Student
    print("✅ Student model imported successfully")
    print("   Student model fields:")
    for column in Student.__table__.columns:
        print(f"   - {column.name}: {column.type}")
except Exception as e:
    print(f"❌ Error: {e}")

# Step 3: Check if there's a registration function conflict
print("\n📋 3. CHECKING REGISTRATION FUNCTIONS...")
try:
    from backend.routes.api import register
    print("✅ Found register function in api.py")
except ImportError as e:
    print(f"⚠️ Could not import from api.py: {e}")

try:
    from routes.auth import register as auth_register
    print("⚠️ Found register function in auth.py - This might be conflicting!")
except ImportError:
    print("✅ No register function in auth.py")

# Step 4: Simulate a registration call
print("\n📋 4. SIMULATING REGISTRATION CALL...")
try:
    from models import User, Student
    
    # This is what's causing the error
    print("\n   ❌ WRONG WAY (What's causing the error):")
    try:
        user = User(
            username="testuser",
            email="test@test.com",
            first_name="Test",  # This line causes the error
            last_name="User",    # This line causes the error
            password_hash="hash"
        )
        print("   This should have failed but didn't - check your User model")
    except TypeError as e:
        print(f"   ✅ Error caught: {e}")
        print(f"   This confirms: User model does NOT have 'first_name' field")
    
    print("\n   ✅ CORRECT WAY:")
    try:
        user = User(
            username="testuser",
            email="test@test.com",
            password_hash="hash",
            role="student",
            is_active=True,
            is_verified=False
        )
        print("   ✅ User created successfully!")
        
        student = Student(
            user=user,
            student_number="GIPS/2024/00001",
            first_name="Test",   # ✅ This is correct
            last_name="User",     # ✅ This is correct
            email="test@test.com"
        )
        print("   ✅ Student created successfully!")
        print("   ✅ This is the correct way to create a user and student")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Step 5: Check your api.py registration function
print("\n📋 5. CHECKING YOUR API.PY REGISTRATION FUNCTION...")
try:
    with open('backend/routes/api.py', 'r') as f:
        content = f.read()
        if "User(" in content:
            # Find the User creation lines
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "User(" in line and "first_name" in line:
                    print(f"   ⚠️ Found problematic line at line {i+1}:")
                    print(f"   {line.strip()}")
                if "User(" in line and "last_name" in line:
                    print(f"   ⚠️ Found problematic line at line {i+1}:")
                    print(f"   {line.strip()}")
        else:
            print("   ✅ No User creation found in api.py")
except Exception as e:
    print(f"   ❌ Could not read api.py: {e}")

# Step 6: Check your auth.py registration function
print("\n📋 6. CHECKING YOUR AUTH.PY REGISTRATION FUNCTION...")
try:
    with open('routes/auth.py', 'r') as f:
        content = f.read()
        if "User(" in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "User(" in line and "first_name" in line:
                    print(f"   ⚠️ Found problematic line in auth.py at line {i+1}:")
                    print(f"   {line.strip()}")
                if "User(" in line and "last_name" in line:
                    print(f"   ⚠️ Found problematic line in auth.py at line {i+1}:")
                    print(f"   {line.strip()}")
except FileNotFoundError:
    print("   ℹ️ auth.py not found - that's fine")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*60)
print("🎯 SOLUTION:")
print("="*60)
print("""
The error 'first_name' is an invalid keyword argument for User means you're trying to pass
'first_name' to the User model when creating a user.

FIX: In your registration function, remove 'first_name' and 'last_name' from the User creation.
They should only be added to the Student creation.

CORRECT CODE:
```python
# Create user - NO first_name/last_name
user = User(
    username=data['username'],
    email=data['email'],
    password_hash=generate_password_hash(data['password']),
    role='student',
    is_active=True,
    is_verified=False
)

# Create student - first_name/last_name go HERE
student = Student(
    user=user,
    student_number=student_number,
    first_name=data['first_name'],  # ✅
    last_name=data['last_name'],    # ✅
    # ... other fields
)