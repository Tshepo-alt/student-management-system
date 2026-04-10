# insert_all_modules.py
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

# Helper: check if module exists
def module_exists(code):
    cur.execute("SELECT id FROM modules WHERE module_code = %s", (code,))
    return cur.fetchone() is not None

# Helper: insert module
def insert_module(code, name, credits, year_level, semester, module_type='core'):
    if not module_exists(code):
        cur.execute("""
            INSERT INTO modules (module_code, module_name, credits, year_level, semester, module_type, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
        """, (code, name, credits, year_level, semester, module_type))
        print(f"Inserted module {code}")
        return True
    else:
        print(f"Module {code} already exists")
        return False

# Helper: link module to program
def link_module_to_program(program_id, module_id, is_compulsory=1):
    cur.execute("SELECT id FROM program_modules WHERE program_id = %s AND module_id = %s", (program_id, module_id))
    if not cur.fetchone():
        cur.execute("INSERT INTO program_modules (program_id, module_id, is_compulsory) VALUES (%s, %s, %s)", (program_id, module_id, is_compulsory))
        print(f"Linked module ID {module_id} to program ID {program_id}")
        return True
    return False

# ========== 1. BSc Computer Science modules (as previously defined) ==========
cs_modules = [
    # Year 1
    ('CS101', 'Introduction to Computer Science', 15, 1, 1, 'core'),
    ('CS102', 'Programming Fundamentals (Python/Java)', 15, 1, 1, 'core'),
    ('CS103', 'Computer Systems & Architecture', 15, 1, 1, 'core'),
    ('CS104', 'Mathematics for Computing', 15, 1, 1, 'core'),
    ('CS105', 'Communication & Academic Writing', 10, 1, 1, 'core'),
    ('CS106', 'Introduction to Databases', 15, 1, 2, 'core'),
    ('CS107', 'Web Development Fundamentals', 15, 1, 2, 'core'),
    # Year 2
    ('CS201', 'Object-Oriented Programming (Java)', 15, 2, 1, 'core'),
    ('CS202', 'Data Structures & Algorithms', 15, 2, 1, 'core'),
    ('CS203', 'Operating Systems', 15, 2, 1, 'core'),
    ('CS204', 'Computer Networks', 15, 2, 1, 'core'),
    ('CS205', 'Software Engineering', 15, 2, 1, 'core'),
    ('CS206', 'Database Systems (SQL/MySQL)', 15, 2, 2, 'core'),
    ('CS207', 'Systems Analysis & Design', 15, 2, 2, 'core'),
    # Year 3
    ('CS301', 'Advanced Java Programming', 15, 3, 1, 'core'),
    ('CS302', 'Web Application Development', 15, 3, 1, 'core'),
    ('CS303', 'Mobile Application Development', 15, 3, 1, 'core'),
    ('CS304', 'Artificial Intelligence', 15, 3, 1, 'core'),
    ('CS305', 'Cybersecurity Fundamentals', 15, 3, 1, 'core'),
    ('CS306', 'Distributed Systems / Cloud Computing', 15, 3, 2, 'core'),
    ('CS307', 'Human Computer Interaction (HCI)', 10, 3, 2, 'core'),
    # Year 4
    ('CS401', 'Final Year Project / Dissertation', 30, 4, 1, 'core'),
    ('CS402', 'Advanced Software Engineering', 15, 4, 1, 'core'),
    ('CS403', 'Data Science / Machine Learning', 15, 4, 1, 'core'),
    ('CS404', 'IT Project Management', 15, 4, 1, 'core'),
    ('CS405', 'Entrepreneurship & Innovation', 10, 4, 1, 'core'),
    ('CS406', 'Industrial Attachment / Internship', 15, 4, 2, 'core'),
]

# ========== 2. BBA Business Management modules ==========
bba_modules = [
    # Year 1
    ('BBA101', 'Principles of Management', 15, 1, 1, 'core'),
    ('BBA102', 'Business Communication', 15, 1, 1, 'core'),
    ('BBA103', 'Financial Accounting', 15, 1, 1, 'core'),
    ('BBA104', 'Marketing Fundamentals', 15, 1, 1, 'core'),
    ('BBA105', 'Business Mathematics', 15, 1, 1, 'core'),
    ('BBA106', 'Introduction to Economics', 15, 1, 2, 'core'),
    ('BBA107', 'Business Law', 15, 1, 2, 'core'),
    # Year 2
    ('BBA201', 'Organizational Behavior', 15, 2, 1, 'core'),
    ('BBA202', 'Human Resource Management', 15, 2, 1, 'core'),
    ('BBA203', 'Operations Management', 15, 2, 1, 'core'),
    ('BBA204', 'Financial Management', 15, 2, 1, 'core'),
    ('BBA205', 'Research Methods', 15, 2, 2, 'core'),
    ('BBA206', 'Business Ethics', 15, 2, 2, 'core'),
    # Year 3
    ('BBA301', 'Strategic Management', 15, 3, 1, 'core'),
    ('BBA302', 'Entrepreneurship', 15, 3, 1, 'core'),
    ('BBA303', 'International Business', 15, 3, 1, 'core'),
    ('BBA304', 'Supply Chain Management', 15, 3, 1, 'core'),
    ('BBA305', 'Project Management', 15, 3, 2, 'core'),
    # Year 4
    ('BBA401', 'Business Research Project', 30, 4, 1, 'core'),
    ('BBA402', 'Leadership and Change Management', 15, 4, 1, 'core'),
    ('BBA403', 'Corporate Governance', 15, 4, 1, 'core'),
    ('BBA404', 'Strategic Marketing', 15, 4, 2, 'core'),
]

# ========== 3. Certificate and Diploma programs (generic but enough) ==========
# For Certificate programs (1 year)
cert_modules = [
    ('CERT101', 'Introduction to Subject Area', 15, 1, 1, 'core'),
    ('CERT102', 'Basic Practical Skills', 15, 1, 1, 'core'),
    ('CERT103', 'Communication and Numeracy', 15, 1, 1, 'core'),
    ('CERT104', 'Workplace Safety', 15, 1, 2, 'core'),
]

# For Diploma programs (3 years)
diploma_modules = [
    ('DIP101', 'Foundation Studies', 15, 1, 1, 'core'),
    ('DIP102', 'Core Subject A', 15, 1, 1, 'core'),
    ('DIP103', 'Core Subject B', 15, 1, 1, 'core'),
    ('DIP104', 'Practical Applications', 15, 1, 2, 'core'),
    ('DIP201', 'Intermediate Studies', 15, 2, 1, 'core'),
    ('DIP202', 'Industry Practice', 15, 2, 1, 'core'),
    ('DIP203', 'Professional Ethics', 15, 2, 2, 'core'),
    ('DIP301', 'Final Year Project', 30, 3, 1, 'core'),
    ('DIP302', 'Career Development', 15, 3, 1, 'core'),
]

# ========== 4. Insert all modules ==========
print("Inserting BSc Computer Science modules...")
for mod in cs_modules:
    insert_module(*mod)

print("\nInserting BBA Business Management modules...")
for mod in bba_modules:
    insert_module(*mod)

print("\nInserting Certificate modules...")
for mod in cert_modules:
    insert_module(*mod)

print("\nInserting Diploma modules...")
for mod in diploma_modules:
    insert_module(*mod)

# ========== 5. Link modules to programs based on program_code ==========
# Get all programs
cur.execute("SELECT id, program_code, duration_years FROM programs")
programs = cur.fetchall()

# For each program, determine which module set to use
for prog_id, prog_code, duration in programs:
    if prog_code == 'BSC-CS':
        module_set = cs_modules
    elif prog_code == 'BBA-BM':
        module_set = bba_modules
    elif prog_code.startswith('CERT') or 'CERT' in prog_code.upper():
        module_set = cert_modules
    elif prog_code.startswith('DIP') or 'DIP' in prog_code.upper():
        module_set = diploma_modules
    else:
        # For any other program (e.g., other certificates/diplomas), use generic modules based on duration
        if duration == 1:
            module_set = cert_modules
        elif duration == 3:
            module_set = diploma_modules
        else:
            # For any other program, use a mix (fallback to generic)
            module_set = cert_modules if duration == 1 else diploma_modules if duration == 3 else cs_modules[:5]

    print(f"\nLinking modules to program {prog_code} (ID {prog_id})...")
    for mod in module_set:
        code = mod[0]
        cur.execute("SELECT id FROM modules WHERE module_code = %s", (code,))
        mod_row = cur.fetchone()
        if mod_row:
            module_id = mod_row[0]
            link_module_to_program(prog_id, module_id)

conn.commit()
cur.close()
conn.close()
print("\nAll modules inserted and linked successfully.")