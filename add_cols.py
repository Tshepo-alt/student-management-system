import pymysql

host = "gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com"
port = 23797
user = "avnadmin"
password = "AVNS_HF4i45zHKHoKx1IxIDV"
database = "gips_college_db"   # <-- CHANGE THIS to your real database name

try:
    conn = pymysql.connect(
        host=host, user=user, password=password, database=database,
        port=port, ssl={'ssl': True}
    )
    cursor = conn.cursor()
    for col in ["bgcse_certificate_path", "id_document_path", "passport_photo_path"]:
        try:
            cursor.execute(f"ALTER TABLE students ADD COLUMN {col} VARCHAR(500);")
            print(f"✅ Added {col}")
        except Exception as e:
            print(f"⚠️ {col}: {e}")
    conn.commit()
    conn.close()
    print("🎉 Done.")
except Exception as e:
    print(f"❌ Error: {e}")