# update_admin_role.py
import os
import sys
from urllib.parse import urlparse
import pymysql
from getpass import getpass

# Get database URL from environment or input
database_url = input("Paste your DATABASE_URL from Render: ").strip()

if not database_url:
    print("❌ DATABASE_URL is required")
    sys.exit(1)

# Parse the URL
parsed = urlparse(database_url)

# Extract connection parameters
db_user = parsed.username
db_password = parsed.password
db_host = parsed.hostname
db_port = parsed.port or 3306
db_name = parsed.path.lstrip('/')

# Determine if SSL is needed (Aiven requires SSL)
ssl_required = '.aivencloud.com' in db_host

print(f"Connecting to {db_host}:{db_port}/{db_name} as {db_user}")
print(f"SSL enabled: {ssl_required}")

# Connect to database
try:
    if ssl_required:
        # For Aiven, we need SSL but no certificate required (use system CA)
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port,
            ssl={'ssl': True}  # This forces SSL without a specific CA cert
        )
    else:
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port
        )
    print("✅ Connected to database")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

try:
    with connection.cursor() as cursor:
        # First check if the user exists
        check_sql = "SELECT id, email, role FROM users WHERE email = %s"
        cursor.execute(check_sql, ('admin@gipscollege.edu.bw',))
        user = cursor.fetchone()
        
        if user:
            print(f"Found user: ID={user[0]}, Email={user[1]}, Current role={user[2]}")
            
            # Update role to admin
            update_sql = "UPDATE users SET role = 'admin' WHERE email = %s"
            cursor.execute(update_sql, ('admin@gipscollege.edu.bw',))
            connection.commit()
            
            print(f"✅ Updated role for admin@gipscollege.edu.bw to 'admin'")
            
            # Verify
            cursor.execute(check_sql, ('admin@gipscollege.edu.bw',))
            updated_user = cursor.fetchone()
            print(f"Verification: ID={updated_user[0]}, Email={updated_user[1]}, New role={updated_user[2]}")
        else:
            print("❌ User admin@gipscollege.edu.bw not found")
            print("You may need to create the admin user first using the registration form or manual insert")
            
            # Optionally create the user (requires password hash)
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('Admin123!')
            insert_sql = """
                INSERT INTO users (username, email, password_hash, role, is_active, is_verified, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(insert_sql, ('admin', 'admin@gipscollege.edu.bw', password_hash, 'admin', 1, 1))
            connection.commit()
            print("✅ Created new admin user")
            
except Exception as e:
    print(f"❌ Error: {e}")
    connection.rollback()
finally:
    connection.close()