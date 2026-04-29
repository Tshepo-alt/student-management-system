# create_demo_users.py
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config import config
from models import db, User, Student, Program, Campus
from werkzeug.security import generate_password_hash

app = Flask(__name__)
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])
db.init_app(app)

def create_user(email, password, role, first_name=None, last_name=None):
    """Create a user if not exists. Returns the user object."""
    existing = User.query.filter_by(email=email).first()
    if existing:
        print(f"User {email} already exists (role={existing.role})")
        return existing
    user = User(
        username=email.split('@')[0],
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        is_active=True,
        is_verified=True
    )
    db.session.add(user)
    db.session.flush()  # to get user.id
    # For student role, also create Student record
    if role == 'student':
        # Get first available program and campus (or create dummy ones if none exist)
        program = Program.query.first()
        campus = Campus.query.first()
        if not program or not campus:
            print("⚠️ No program or campus found. Student record will be incomplete.")
        # Generate student number
        year = 2026
        student_count = Student.query.count() + 1
        student_number = f"GIPS/{year}/{student_count:05d}"
        student = Student(
            user_id=user.id,
            student_number=student_number,
            first_name=first_name or email.split('@')[0].capitalize(),
            last_name=last_name or "User",
            email=email,
            phone="+26770000000",
            program_id=program.id if program else None,
            campus_id=campus.id if campus else None,
            admission_status='accepted',
            is_government_sponsored=False,
            wants_accommodation=False,
            enrollment_date=db.func.current_date()
        )
        db.session.add(student)
        print(f"  -> Created Student record for {email}: {student_number}")
    db.session.commit()
    print(f"Created user: {email} -> {role}")
    return user

def main():
    with app.app_context():
        # Define users to create
        users_data = [
            ("admin@gipscollege.edu.bw", "Admin123!", "admin", "System", "Administrator"),
            ("registrar@gipscollege.edu.bw", "Admin123!", "registrar", "Registrar", "Office"),
            ("finance@gipscollege.edu.bw", "Admin123!", "finance", "Finance", "Officer"),
            ("lecturer@example.com", "Admin123!", "lecturer", "Lecturer", "User"),
            ("accommodation@gipscollege.edu.bw", "Admin123!", "staff", "Accommodation", "Officer"),
            ("student@example.com", "Student123!", "student", "Test", "Student"),
            ("alumni@example.com", "Student123!", "alumni", "Alumni", "User"),
        ]
        for email, password, role, first, last in users_data:
            create_user(email, password, role, first, last)

        print("\n✅ Demo users created/verified in database.")
        print("\nYou can now log in with the credentials from your login.html demo buttons.")

if __name__ == '__main__':
    main()