import pymysql

# Your Aiven/MySQL connection details
host = "gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com"
port = 23797
user = "avnadmin"
password = "AVNS_HF4i45zHKHoKx1IxIDV"
database = "gips_college_db"

# SQL to add the column if it doesn't exist
add_column_sql = """
ALTER TABLE students ADD COLUMN moodle_user_id INT UNIQUE
"""

# Check if column already exists
check_column_sql = """
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_name = 'students' AND column_name = 'moodle_user_id'
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
            print("Column 'moodle_user_id' not found. Adding it...")
            cursor.execute(add_column_sql)
            connection.commit()
            print("✅ Column 'moodle_user_id' added successfully!")
        else:
            print("Column 'moodle_user_id' already exists. Nothing to do.")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'connection' in locals():
        connection.close()