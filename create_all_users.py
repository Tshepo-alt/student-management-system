#!/usr/bin/env python
"""
Create all required users (admins and sample students) for the GIPS College system.
Run this script once to populate the database with test users.
"""

import os
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the app factory and models from the same location as app.py
try:
    from app import create_app
except ImportError:
    print("❌ Could not import create_app from app.py. Make sure you are in the project root.")
    sys.exit(1)

# Import models from the same module that app.py uses
# In app.py: from models import db, User
try:
    from models import db, User, Student, Program
    print("✅ Imported models from models (same as app.py)")
except ImportError:
    # Fallback: try backend.models if models is not found
    try:
        from backend.models import db, User, Student, Program
        print("✅ Imported models from backend.models")
    except ImportError:
        print("❌ Could not import models. Check your project structure.")
        sys.exit(1)

def create_default_admins(app):
    """Create admin users from ADMIN_EMAILS and ensure extra admins exist."""
    admin_emails = os.getenv('ADMIN_EMAILS', '').split(',')
    admin_roles = os.getenv('ADMIN_ROLES', '').split(',')
    default_password = 'Admin123!'   # Change if needed

    # Extra admins to ensure exist (useful for testing)
    extra_admins = [
        ('finance', 'finance@gipscollege.edu.bw', 'finance'),
        ('accommodation', 'accommodation@gipscollege.edu.bw', 'staff'),
        ('lecturer', 'lecturer@example.com', 'lecturer')
    ]

    with app.app_context():
        # Create admins from ADMIN_EMAILS
        for email, role in zip(admin_emails, admin_roles):
            email = email.strip()
            if not email:
                continue
            user = User.query.filter_by(email=email).first()
            if user:
                print(f"⚠️ Admin user already exists: {email}")
                continue
            user = User(
                username=email.split('@')[0],
                email=email,
                password_hash=generate_password_hash(default_password),
                role=role,
                is_active=True,
                is_verified=True
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created admin: {email} (role: {role})")

        # Create extra admins
        for username, email, role in extra_admins:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(default_password),
                    role=role,
                    is_active=True,
                    is_verified=True
                )
                db.session.add(user)
                db.session.commit()
                print(f"✅ Created extra user: {email} (role: {role})")

def create_sample_students(app):
    """Create sample student accounts."""
    with app.app_context():
        # Find a program to assign students to (prefer BSC-CS, which exists in your schema)
        prog = Program.query.filter_by(program_code='BSC-CS').first()
        if not prog:
            prog = Program.query.first()
            if not prog:
                print("❌ No programs found in database. Cannot create students.")
                return
        print(f"📚 Using program: {prog.program_code} (id={prog.id})")

        # Sample student data (adjust fields to match your model)
        students_data = [
            {
                'username': 'john.doe',
                'email': 'john.doe@student.gipscollege.edu.bw',
                'first_name': 'John',
                'last_name': 'Doe',
                'student_number': '2024-001',
                'program_id': prog.id,
                'campus_id': prog.campus_id,  # if your student model has campus_id
                'enrollment_date': '2024-07-01',
                'current_year': 1,
                'admission_status': 'accepted',
                'academic_status': 'good_standing',
                'is_active': True
            },
            {
                'username': 'jane.smith',
                'email': 'jane.smith@student.gipscollege.edu.bw',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'student_number': '2024-002',
                'program_id': prog.id,
                'campus_id': prog.campus_id,
                'enrollment_date': '2024-07-01',
                'current_year': 1,
                'admission_status': 'accepted',
                'academic_status': 'good_standing',
                'is_active': True
            },
            {
                'username': 'bob.johnson',
                'email': 'bob.johnson@student.gipscollege.edu.bw',
                'first_name': 'Bob',
                'last_name': 'Johnson',
                'student_number': '2024-003',
                'program_id': prog.id,
                'campus_id': prog.campus_id,
                'enrollment_date': '2024-07-01',
                'current_year': 1,
                'admission_status': 'accepted',
                'academic_status': 'good_standing',
                'is_active': True
            }
        ]

        default_password = 'Student123!'

        # Get column names of Student model to filter fields
        student_columns = [c.name for c in Student.__table__.columns]
        print(f"📋 Student model columns: {student_columns}")

        for data in students_data:
            # Check if user already exists
            user = User.query.filter_by(email=data['email']).first()
            if user:
                print(f"⚠️ Student user already exists: {data['email']}")
                continue

            # Create user account
            user = User(
                username=data['username'],
                email=data['email'],
                password_hash=generate_password_hash(default_password),
                role='student',
                is_active=True,
                is_verified=True
            )
            db.session.add(user)
            db.session.flush()  # to get user.id

            # Build student record with only existing fields
            student_kwargs = {'user_id': user.id}
            for key in data:
                if key in student_columns:
                    student_kwargs[key] = data[key]
            # Add email if the model requires it
            if 'email' in student_columns and 'email' not in student_kwargs:
                student_kwargs['email'] = data['email']
            # Add first_name, last_name if present
            if 'first_name' in student_columns:
                student_kwargs['first_name'] = data['first_name']
            if 'last_name' in student_columns:
                student_kwargs['last_name'] = data['last_name']
            if 'student_number' in student_columns:
                student_kwargs['student_number'] = data['student_number']
            if 'program_id' in student_columns:
                student_kwargs['program_id'] = data['program_id']
            if 'campus_id' in student_columns:
                student_kwargs['campus_id'] = data['campus_id']
            if 'enrollment_date' in student_columns:
                student_kwargs['enrollment_date'] = data['enrollment_date']
            if 'current_year' in student_columns:
                student_kwargs['current_year'] = data['current_year']
            if 'admission_status' in student_columns:
                student_kwargs['admission_status'] = data['admission_status']
            if 'academic_status' in student_columns:
                student_kwargs['academic_status'] = data['academic_status']
            if 'is_active' in student_columns:
                student_kwargs['is_active'] = data['is_active']

            student = Student(**student_kwargs)
            db.session.add(student)
            db.session.commit()
            print(f"✅ Created student: {data['email']} (username: {data['username']})")

def main():
    app = create_app()   # This creates the Flask app (includes database init)
    print("🚀 Creating GIPS College users...")
    create_default_admins(app)
    create_sample_students(app)
    print("✨ Done! All users created successfully.")
    print("\n📋 Login credentials:")
    print("   Admins (email: admin@gipscollege.edu.bw, password: Admin123!)")
    print("   Students (email: john.doe@student.gipscollege.edu.bw, password: Student123!)")

if __name__ == '__main__':
    main()