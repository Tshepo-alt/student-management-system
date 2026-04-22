import pymysql

conn = pymysql.connect(
    host='gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com',
    port=23797,
    user='avnadmin',
    password='AVNS_HF4i45zHKHoKx1IxIDV',
    database='gips_college_db',
    ssl={'ssl': True}
)
cur = conn.cursor()

# Check existing courses
cur.execute("SELECT id, course_code, course_name, lecturer_id FROM courses")
courses = cur.fetchall()
print("Courses:")
for row in courses:
    print(f"ID: {row[0]}, Code: {row[1]}, Name: {row[2]}, Lecturer ID: {row[3]}")

# Check lecturers
cur.execute("SELECT id, username, email FROM users WHERE role = 'lecturer'")
lecturers = cur.fetchall()
print("\nLecturers:")
for row in lecturers:
    print(f"ID: {row[0]}, Username: {row[1]}, Email: {row[2]}")

# If we have a lecturer (assume ID 4), assign all courses to that lecturer
if lecturers:
    lecturer_id = lecturers[0][0]
    cur.execute("UPDATE courses SET lecturer_id = %s WHERE lecturer_id IS NULL OR lecturer_id != %s", (lecturer_id, lecturer_id))
    print(f"\nUpdated {cur.rowcount} courses to lecturer ID {lecturer_id}")
else:
    print("\nNo lecturer found. Create one first.")

conn.commit()
cur.close()
conn.close()