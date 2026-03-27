# create_demo_users.py
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models import db, User, Student
from werkzeug.security import generate_password_hash
from flask import Flask
from datetime import datetime

# Create a minimal Flask app context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Admin@localhost:3306/gips_college_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Define demo users: (email, username, role, first_name, last_name, password)
demo_users = [
    # student
    ('student@example.com', 'student', 'student', 'John', 'Doe', 'Student123!'),
    # admin
    ('admin@gipscollege.edu.bw', 'admin', 'admin', 'Admin', 'User', 'Admin@2026!'),
    # registrar
    ('registrar@gipscollege.edu.bw', 'registrar', 'registrar', 'Registrar', 'Officer', 'Registrar@2026!'),
    # finance
    ('finance@gipscollege.edu.bw', 'finance', 'finance', 'Finance', 'Officer', 'Finance@2026!'),
    # accommodation staff
    ('accommodation@gipscollege.edu.bw', 'accommodation_staff', 'staff', 'Accommodation', 'Staff', 'Staff@2026!'),
    # lecturer
    ('lecturer@example.com', 'lecturer', 'lecturer', 'Lecturer', 'User', 'Lecturer@2026!'),
    # alumni
    ('alumni@example.com', 'alumni', 'alumni', 'Alumni', 'User', 'Alumni@2026!'),
]

def create_user(email, username, role, first_name, last_name, password):
    """Create a user and associated student record if needed."""
    with app.app_context():
        # Check if user already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"⚠️ User {email} already exists, skipping.")
            return

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(user)
        db.session.flush()

        # For student and alumni, also create a student record
        if role in ['student', 'alumni']:
            student = Student(
                user_id=user.id,
                student_number=f"DEMO-{username.upper()}",
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(student)

        db.session.commit()
        print(f"✅ Created {role}: {email} / {password}")

def main():
    print("=" * 60)
    print("Creating demo users for GIPS College Portal")
    print("=" * 60)
    for email, username, role, first_name, last_name, password in demo_users:
        create_user(email, username, role, first_name, last_name, password)
    print("=" * 60)
    print("Done! You can now log in with any of these credentials.")
    print("=" * 60)

if __name__ == '__main__':
    main()