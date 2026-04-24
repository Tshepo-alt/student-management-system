import pymysql

# Your Aiven connection details (same as earlier)
host = "gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com"
port = 23797
user = "avnadmin"
password = "AVNS_HF4i45zHKHoKx1IxIDV"   # replace if your password changed
database = "gips_college_db"

create_table_sql = """
CREATE TABLE IF NOT EXISTS student_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject VARCHAR(255) NOT NULL,
    category VARCHAR(100) DEFAULT 'General',
    message TEXT NOT NULL,
    status ENUM('pending', 'in-progress', 'resolved') DEFAULT 'pending',
    responses JSON DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
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
        cursor.execute(create_table_sql)
        connection.commit()
        print("✅ Table 'student_queries' created (or already exists).")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'connection' in locals():
        connection.close()