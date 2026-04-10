# insert_programs.py
import pymysql
from datetime import datetime

conn = pymysql.connect(
    host='gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com',
    port=23797,
    user='avnadmin',
    password='AVNS_HF4i45zHKHoKx1IxIDV',
    database='gips_college_db',
    ssl={'ssl': True}
)
cur = conn.cursor()

# 1. Ensure program types exist
program_types = [
    ('DEG', 'Bachelor Degree', 4, 'Full Bachelor Degree Program (4 years)'),
    ('DIP', 'Diploma', 3, 'Diploma Program (3 years)'),
    ('CERT', 'Certificate', 1, 'Certificate Program (1 year)')
]
for code, name, duration, desc in program_types:
    cur.execute("SELECT id FROM program_types WHERE type_code = %s", (code,))
    if not cur.fetchone():
        cur.execute("INSERT INTO program_types (type_code, type_name, duration_years, description) VALUES (%s, %s, %s, %s)",
                    (code, name, duration, desc))
print("Program types inserted/verified.")

# 2. Ensure faculties exist
faculties = [
    ('FICT', 'Faculty of Information & Communication Technology', 'ICT, Computer Science, and Computing Programs'),
    ('FBA', 'Faculty of Business Administration', 'Business Management, HR, Marketing, Tourism Programs'),
    ('FCA', 'Faculty of Commerce & Accounting', 'Commerce, Accounting, Finance, Supply Chain Programs'),
    ('FET', 'Faculty of Engineering & Technology', 'Automotive, Diesel, and Technical Programs'),
    ('FTH', 'Faculty of Tourism & Hospitality', 'Tourism and Hospitality Programs'),
    ('FCV', 'Faculty of Creative & Vocational', 'Creative Arts and Vocational Programs')
]
for code, name, desc in faculties:
    cur.execute("SELECT id FROM faculties WHERE faculty_code = %s", (code,))
    if not cur.fetchone():
        cur.execute("INSERT INTO faculties (faculty_code, faculty_name, description) VALUES (%s, %s, %s)",
                    (code, name, desc))
print("Faculties inserted/verified.")

# 3. Ensure departments exist (mapped to faculty IDs)
# We'll first get faculty IDs
cur.execute("SELECT id, faculty_code FROM faculties")
faculty_map = {row[1]: row[0] for row in cur.fetchall()}

departments = [
    ('CS', 'Computer Science', 'FICT'),
    ('IT', 'Information Technology', 'FICT'),
    ('DS', 'Data Science', 'FICT'),
    ('CSEC', 'Cyber Security', 'FICT'),
    ('BM', 'Business Management', 'FBA'),
    ('HRM', 'Human Resource Management', 'FBA'),
    ('MKT', 'Marketing', 'FBA'),
    ('ENT', 'Entrepreneurship', 'FBA'),
    ('ACC', 'Accounting', 'FCA'),
    ('FIN', 'Finance', 'FCA'),
    ('BF', 'Banking & Finance', 'FCA'),
    ('SCM', 'Supply Chain Management', 'FCA'),
    ('PS', 'Purchasing & Supply', 'FCA'),
    ('FAF', 'Forensic Accounting & Finance', 'FCA'),
    ('AUTO', 'Automotive Engineering', 'FET'),
    ('DIESEL', 'Diesel Plant Engineering', 'FET'),
    ('AELEC', 'Automotive Electronics', 'FET'),
    ('TM', 'Travel & Tourism Management', 'FTH'),
    ('HM', 'Hospitality Management', 'FTH'),
    ('EM', 'Event Management', 'FTH'),
    ('FD', 'Fashion Design', 'FCV'),
    ('BT', 'Beauty Therapy', 'FCV'),
    ('HD', 'Hairdressing & Barbering', 'FCV')
]
for code, name, faculty_code in departments:
    faculty_id = faculty_map.get(faculty_code)
    if faculty_id:
        cur.execute("SELECT id FROM departments WHERE department_code = %s", (code,))
        if not cur.fetchone():
            cur.execute("INSERT INTO departments (department_code, department_name, faculty_id) VALUES (%s, %s, %s)",
                        (code, name, faculty_id))
print("Departments inserted/verified.")

# 4. Ensure campuses exist (we inserted earlier, but verify)
cur.execute("SELECT id, campus_code FROM campuses")
campus_map = {row[1]: row[0] for row in cur.fetchall()}
if not campus_map:
    # Insert default campuses if missing
    cur.execute('''
        INSERT INTO campuses (campus_code, campus_name, campus_location, has_accommodation, is_main_campus)
        VALUES 
        ('GAB-MAIN', 'Gaborone Main Campus', 'Block 6 Along Molepolole Road', TRUE, TRUE),
        ('GAB-MALL', 'Gaborone Main Mall Campus', 'Gaborone Central Business District', FALSE, FALSE),
        ('FRANC', 'Francistown Campus', 'Francistown', FALSE, FALSE),
        ('MAUN', 'Maun Campus', 'Maun', FALSE, FALSE)
    ''')
    conn.commit()
    cur.execute("SELECT id, campus_code FROM campuses")
    campus_map = {row[1]: row[0] for row in cur.fetchall()}
print("Campuses ready.")

# 5. Get program type IDs
cur.execute("SELECT id, type_code FROM program_types")
program_type_map = {row[1]: row[0] for row in cur.fetchall()}

# 6. Insert all programs (based on original SQL schema)
# Program list: (program_code, program_name, type_code, faculty_code, department_code, campus_code, duration_years, min_bgcse_points)
programs = [
    # Main Campus (GAB-MAIN) programs
    ('BSC-CS', 'Bachelor of Science in Computer Science', 'DEG', 'FICT', 'CS', 'GAB-MAIN', 4, 32),
    ('BBA-BM', 'Bachelor of Business Administration', 'DEG', 'FBA', 'BM', 'GAB-MAIN', 4, 32),
    ('NCC-DIP3', 'NCC Diploma in Computing (Level 3)', 'DIP', 'FICT', 'IT', 'GAB-MAIN', 1, 28),
    ('CERT-IT', 'Certificate in Information Technology', 'CERT', 'FICT', 'IT', 'GAB-MAIN', 1, 24),
    ('DS-CERT', 'Data Science Certificate', 'CERT', 'FICT', 'DS', 'GAB-MAIN', 1, 24),
    # Main Mall Campus (GAB-MALL)
    ('CERT-IT-MALL', 'Certificate in Information Technology', 'CERT', 'FICT', 'IT', 'GAB-MALL', 1, 20),
    ('CERT-BM-MALL', 'Certificate in Business Management', 'CERT', 'FBA', 'BM', 'GAB-MALL', 1, 20),
    # Francistown Campus (FRANC)
    ('CERT-IT-FRANC', 'Certificate in Information Technology', 'CERT', 'FICT', 'IT', 'FRANC', 1, 20),
    ('CERT-BM-FRANC', 'Certificate in Business Management', 'CERT', 'FBA', 'BM', 'FRANC', 1, 20),
    # Maun Campus (MAUN)
    ('CERT-TT-MAUN', 'Certificate in Travel & Tourism', 'CERT', 'FTH', 'TM', 'MAUN', 1, 20),
    ('CERT-HM-MAUN', 'Certificate in Hospitality Management', 'CERT', 'FTH', 'HM', 'MAUN', 1, 20),
    # Additional programs from original schema (if any) – add more as needed
    ('BCOM-ACC', 'Bachelor of Commerce in Accounting', 'DEG', 'FCA', 'ACC', 'GAB-MAIN', 4, 32),
    ('BCOM-FIN', 'Bachelor of Commerce in Finance', 'DEG', 'FCA', 'FIN', 'GAB-MAIN', 4, 32),
    ('DIP-BM', 'Diploma in Business Management', 'DIP', 'FBA', 'BM', 'GAB-MAIN', 3, 28),
    ('DIP-IT', 'Diploma in Information Technology', 'DIP', 'FICT', 'IT', 'GAB-MAIN', 3, 28),
]

for prog in programs:
    prog_code, name, type_code, faculty_code, dept_code, campus_code, duration, min_points = prog
    program_type_id = program_type_map.get(type_code)
    faculty_id = faculty_map.get(faculty_code)
    dept_id = None
    cur.execute("SELECT id FROM departments WHERE department_code = %s", (dept_code,))
    dept_row = cur.fetchone()
    if dept_row:
        dept_id = dept_row[0]
    campus_id = campus_map.get(campus_code)
    if not campus_id:
        print(f"Warning: Campus {campus_code} not found, skipping {prog_code}")
        continue
    cur.execute("SELECT id FROM programs WHERE program_code = %s", (prog_code,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO programs (program_code, program_name, program_type_id, faculty_id, department_id, campus_id, duration_years, min_bgcse_points, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        """, (prog_code, name, program_type_id, faculty_id, dept_id, campus_id, duration, min_points))
        print(f"Inserted program {prog_code}")
    else:
        print(f"Program {prog_code} already exists")

conn.commit()
cur.close()
conn.close()
print("All programs inserted successfully!")