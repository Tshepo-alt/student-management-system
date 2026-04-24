# add_columns.py
import pymysql
from getpass import getpass

# Connection details (from your Aiven Console)
host = "gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com"
port = 23797
user = "avnadmin"
database = "defaultdb"

print("🔐 Please enter your Aiven database password:")
password = getpass()  # this hides the input

try:
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        ssl={'ssl': True}   # Aiven requires SSL
    )
    print("✅ Connected to database")

    with connection.cursor() as cursor:
        # Try to add each column – errors are ignored if already present
        columns = [
            "bgcse_certificate_path",
            "id_document_path",
            "passport_photo_path"
        ]
        for col in columns:
            try:
                cursor.execute(f"ALTER TABLE students ADD COLUMN {col} VARCHAR(500);")
                print(f"✅ Added column: {col}")
            except Exception as e:
                if "Duplicate column" in str(e):
                    print(f"⚠️ Column {col} already exists – skipping")
                else:
                    print(f"⚠️ Could not add {col}: {e}")
        connection.commit()

    print("\n🎉 All columns processed.")

except Exception as e:
    print(f"❌ Connection or SQL error: {e}")

finally:
    if 'connection' in locals():
        connection.close()