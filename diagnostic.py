import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'backend'))

print("="*60)
print("DATABASE DIAGNOSTIC")
print("="*60)

# Test 1: Check if pymysql is installed
try:
    import pymysql
    print("✅ pymysql is installed")
except ImportError:
    print("❌ pymysql is NOT installed. Run: pip install pymysql")
    exit(1)

# Test 2: Try to connect directly to MySQL
try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='Admin',
        port=3306
    )
    print("✅ MySQL connection successful!")
    
    # Check if database exists
    with conn.cursor() as cursor:
        cursor.execute("SHOW DATABASES LIKE 'gips_college_db'")
        result = cursor.fetchone()
        if result:
            print("✅ Database 'gips_college_db' exists")
        else:
            print("❌ Database 'gips_college_db' does NOT exist")
            print("   Creating database...")
            cursor.execute("CREATE DATABASE gips_college_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("✅ Database created!")
    conn.close()
except Exception as e:
    print(f"❌ MySQL connection failed: {e}")
    print("   Please check:")
    print("   - MySQL is running (service MySQL80 is running)")
    print("   - Password is correct (trying 'Admin')")
    print("   - Host is localhost")
    exit(1)

# Test 3: Try to import Flask app and create tables
print("\n" + "="*60)
print("FLASK APP DATABASE TEST")
print("="*60)

try:
    from app import create_app
    from models import db
    
    app = create_app()
    print("✅ Flask app created")
    
    with app.app_context():
        # Test connection
        result = db.session.execute("SELECT 1").scalar()
        print(f"✅ Database query successful: {result}")
        
        # Create tables if they don't exist
        db.create_all()
        print("✅ Tables created/verified")
        
        # Check tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 Tables in database: {len(tables)}")
        
        # Check users table
        from models import User
        user_count = User.query.count()
        print(f"👥 Total users: {user_count}")
        
        # Check for admin users
        admins = User.query.filter(User.role.in_(['admin', 'administrator'])).all()
        print(f"👑 Admin users: {len(admins)}")
        for admin in admins:
            print(f"   - {admin.email} (role: {admin.role})")
        
        print("\n✅ All tests passed! Database is ready.")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
