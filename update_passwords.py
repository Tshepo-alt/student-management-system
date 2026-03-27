# update_passwords.py
from werkzeug.security import generate_password_hash
import pymysql

# Database connection
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Admin',
    database='gips_college_db',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cursor:
        # Generate new hashes
        admin_hash = generate_password_hash('Admin123!')
        student_hash = generate_password_hash('Student123!')
        
        print(f"Admin hash: {admin_hash}")
        print(f"Student hash: {student_hash}")
        
        # Update admin-type users (including admin, registrar, finance, lecturer, staff, accommodation)
        admin_emails = [
            'admin@gipscollege.edu.bw',
            'registrar@gipscollege.edu.bw',
            'finance@gipscollege.edu.bw',
            'lecturer@example.com',
            'staff@example.com',
            'accommodation@gipscollege.edu.bw'
        ]
        for email in admin_emails:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (admin_hash, email)
            )
            print(f"Updated {email}")
        
        # Update student and alumni
        student_emails = ['student@example.com', 'alumni@example.com']
        for email in student_emails:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (student_hash, email)
            )
            print(f"Updated {email}")
        
        conn.commit()
        print("✅ All passwords updated successfully!")

finally:
    conn.close()