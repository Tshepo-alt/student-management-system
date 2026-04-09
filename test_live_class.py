import pymysql
import requests
import json
import sys

# Database connection details
DB_CONFIG = {
    'host': 'gips-college-db-sekokonyanetshepo045-f106.k.aivencloud.com',
    'port': 23797,
    'user': 'avnadmin',
    'password': 'AVNS_HF4i45zHKHoKx1IxIDV',
    'database': 'gips_college_db',
    'ssl': {'ssl': True}
}

def get_lecturer_courses():
    """Get all courses assigned to a lecturer (user with role 'lecturer')"""
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    # Find a lecturer user
    cur.execute("SELECT id, username, email FROM users WHERE role = 'lecturer' LIMIT 1")
    lecturer = cur.fetchone()
    if not lecturer:
        print("No lecturer user found in the database.")
        print("Please create a lecturer user first or promote an existing user.")
        return None, []
    
    lecturer_id, username, email = lecturer
    print(f"Found lecturer: {username} (ID: {lecturer_id}, Email: {email})")
    
    # Get courses assigned to this lecturer
    cur.execute("SELECT id, course_code, course_name FROM courses WHERE lecturer_id = %s", (lecturer_id,))
    courses = cur.fetchall()
    cur.close()
    conn.close()
    
    if not courses:
        print(f"No courses assigned to lecturer {username}. Please assign a course first.")
        return lecturer_id, []
    
    print(f"Found {len(courses)} course(s) for this lecturer:")
    for c in courses:
        print(f"  ID: {c[0]}, Code: {c[1]}, Name: {c[2]}")
    return lecturer_id, courses

def test_start_live_class(course_id, access_token):
    """Test the start live class API endpoint"""
    base_url = "https://student-management-system-lks1.onrender.com"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # First check meeting status
    print(f"\nChecking meeting status for course {course_id}...")
    resp = requests.get(f"{base_url}/api/classes/course/{course_id}/meeting", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    # Try to start a class
    print(f"\nStarting live class for course {course_id}...")
    payload = {'duration': 60}
    resp = requests.post(f"{base_url}/api/classes/course/{course_id}/start", headers=headers, json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    if resp.status_code == 200:
        print("\n✅ Success! Google Meet link created.")
        data = resp.json()
        print(f"Meeting link: {data.get('meeting_link')}")
        print(f"Meeting ID: {data.get('meeting_id')}")
    else:
        print("\n❌ Failed to start class. Check the error message above.")

def main():
    # First, get a valid course from the database
    lecturer_id, courses = get_lecturer_courses()
    if not courses:
        print("\nWould you like to create a test course? (y/n)")
        choice = input().strip().lower()
        if choice == 'y':
            conn = pymysql.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("INSERT INTO courses (course_code, course_name, credits, lecturer_id, is_active) VALUES (%s, %s, %s, %s, 1)",
                        ('TEST101', 'Test Live Class Course', 12, lecturer_id))
            conn.commit()
            new_id = cur.lastrowid
            print(f"Test course created with ID: {new_id}")
            cur.close()
            conn.close()
            courses = [(new_id, 'TEST101', 'Test Live Class Course')]
        else:
            print("Cannot proceed without a course. Exiting.")
            sys.exit(1)
    
    # Now ask for the access token
    print("\nPlease paste your JWT access token from the browser:")
    print("(Log in as a lecturer, open Developer Tools -> Application -> Local Storage -> copy 'access_token')")
    token = input().strip()
    
    if not token:
        print("No token provided. Exiting.")
        sys.exit(1)
    
    # Ask which course to test
    print("\nEnter the course ID to test (from the list above):")
    try:
        course_id = int(input().strip())
    except ValueError:
        print("Invalid course ID. Exiting.")
        sys.exit(1)
    
    test_start_live_class(course_id, token)

if __name__ == "__main__":
    main()