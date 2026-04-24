import pymysql

# Your Aiven connection details (same as before)
host = "gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com"
port = 23797
user = "avnadmin"
password = "AVNS_HF4i45zHKHoKx1IxIDV"  # replace if needed
database = "gips_college_db"  # your actual database name

# SQL to create the staff_queries table
create_table_sql = """
CREATE TABLE IF NOT EXISTS staff_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    staff_id INT NOT NULL,
    staff_name VARCHAR(200) NOT NULL,
    staff_email VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    priority ENUM('high', 'medium', 'low') DEFAULT 'medium',
    status ENUM('pending', 'resolved') DEFAULT 'pending',
    responses JSON DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE CASCADE
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
        print("✅ Table 'staff_queries' created (or already exists).")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'connection' in locals():
        connection.close()