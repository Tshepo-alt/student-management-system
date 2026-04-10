# create_alumni_record.py
import pymysql
from datetime import date

conn = pymysql.connect(
    host='gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com',
    port=23797,
    user='avnadmin',
    password='AVNS_HF4i45zHKHoKx1IxIDV',
    database='gips_college_db',
    ssl={'ssl': True}
)
cur = conn.cursor()

# 1. Find the user with email 'alumni@example.com'
cur.execute("SELECT id FROM users WHERE email = 'alumni@example.com'")
user = cur.fetchone()
if not user:
    print("User alumni@example.com not found. Please register first.")
    exit(1)
user_id = user[0]
print(f"User ID: {user_id}")

# 2. Find or create a student record
cur.execute("SELECT id FROM students WHERE user_id = %s", (user_id,))
student = cur.fetchone()
if not student:
    student_number = f"ALUMNI/{date.today().year}/001"
    cur.execute("""
        INSERT INTO students (user_id, student_number, first_name, last_name, email, enrollment_date, admission_status, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, student_number, 'Alumni', 'User', 'alumni@example.com', date.today(), 'graduated', 1))
    conn.commit()
    cur.execute("SELECT id FROM students WHERE user_id = %s", (user_id,))
    student = cur.fetchone()
student_id = student[0]
print(f"Student ID: {student_id}")

# 3. Create alumni record if not exists
cur.execute("SELECT id FROM alumni WHERE user_id = %s", (user_id,))
if cur.fetchone():
    print("Alumni record already exists.")
else:
    cur.execute("""
        INSERT INTO alumni (user_id, student_id, student_number, graduation_year, employment_status, is_verified)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, student_id, 'ALUMNI001', 2025, 'employed', 1))
    conn.commit()
    print("Alumni record created successfully.")

cur.close()
conn.close()