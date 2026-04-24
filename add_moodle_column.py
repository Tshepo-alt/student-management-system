import pymysql

# Your Aiven connection details (based on your previous script)
host = "gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com"
port = 23797
user = "avnadmin"
password = "AVNS_HF4i45zHKHoKx1IxIDV"
database = "gips_college_db"  # your actual database name

# SQL to add the column if it doesn't exist
add_column_sql = """
ALTER TABLE modules ADD COLUMN moodle_course_id INT UNIQUE
"""

# Check if column already exists (optional but safe)
check_column_sql = """
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_name = 'modules' AND column_name = 'moodle_course_id'
"""

try:
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        ssl={'ssl': True}
    )
    print("✅ Connected to database")

    with connection.cursor() as cursor:
        cursor.execute(check_column_sql)
        exists = cursor.fetchone()[0] > 0

        if not exists:
            print("Column 'moodle_course_id' not found. Adding it...")
            cursor.execute(add_column_sql)
            connection.commit()
            print("✅ Column 'moodle_course_id' added successfully!")
        else:
            print("Column 'moodle_course_id' already exists. Nothing to do.")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'connection' in locals():
        connection.close()