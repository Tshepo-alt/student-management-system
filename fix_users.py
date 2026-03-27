# fix_users.py
import os
import sys
from pathlib import Path
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
        # Admin hash for "Admin123!"
        admin_hash = generate_password_hash('Admin123!')
        # Student hash for "Student123!"
        student_hash = generate_password_hash('Student123!')
        
        # Update admin-type users
        admin_emails = [
            ('admin@gipscollege.edu.bw', 'admin'),
            ('registrar@gipscollege.edu.bw', 'registrar'),
            ('finance@gipscollege.edu.bw', 'finance'),
            ('lecturer@example.com', 'lecturer'),
            ('staff@example.com', 'staff'),
            ('accommodation@gipscollege.edu.bw', 'staff')
        ]
        for email, role in admin_emails:
            cursor.execute(
                "UPDATE users SET password_hash = %s, role = %s, is_active = 1, is_verified = 1 WHERE email = %s",
                (admin_hash, role, email)
            )
            if cursor.rowcount == 0:
                # Insert if not exists
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role, is_active, is_verified) VALUES (%s, %s, %s, %s, 1, 1)",
                    (email.split('@')[0], email, admin_hash, role)
                )
            print(f"Processed {email}")
        
        # Update student and alumni
        student_emails = [
            ('student@example.com', 'student'),
            ('alumni@example.com', 'alumni')
        ]
        for email, role in student_emails:
            cursor.execute(
                "UPDATE users SET password_hash = %s, role = %s, is_active = 1, is_verified = 1 WHERE email = %s",
                (student_hash, role, email)
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role, is_active, is_verified) VALUES (%s, %s, %s, %s, 1, 1)",
                    (email.split('@')[0], email, student_hash, role)
                )
            print(f"Processed {email}")
        
        conn.commit()
        print("✅ All users updated successfully!")
        print("   Passwords: Admin123! for admin roles, Student123! for student/alumni")
        
finally:
    conn.close()