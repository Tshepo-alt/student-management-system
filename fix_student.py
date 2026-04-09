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

cur.execute("SELECT id FROM users WHERE email = 'student@example.com'")
user = cur.fetchone()
if not user:
    print("User student@example.com not found. Please register first.")
else:
    user_id = user[0]
    cur.execute("SELECT id FROM students WHERE user_id = %s", (user_id,))
    if cur.fetchone():
        print("Student record already exists.")
    else:
        year = date.today().year
        cur.execute("SELECT COUNT(*) FROM students")
        count = cur.fetchone()[0] + 1
        student_number = f'GIPS/{year}/{count:05d}'
        cur.execute("""
            INSERT INTO students (user_id, student_number, first_name, last_name, email, enrollment_date, admission_status, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, student_number, 'Student', 'Test', 'student@example.com', date.today(), 'accepted', 1))
        conn.commit()
        print(f"Student record created with number {student_number}")

cur.close()
conn.close()
