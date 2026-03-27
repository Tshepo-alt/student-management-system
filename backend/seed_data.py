"""
Seed database with sample data
Run this once to populate the database
"""

from app import create_app, db
from models import (
    User, Program, Course, Student, Assignment, 
    Accommodation, Payment, ExamRegistration
)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def seed_database():
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        print("✅ Creating Programs...")
        programs = [
            Program(name='Computer Science', code='CS', duration_years=4),
            Program(name='Business Administration', code='BA', duration_years=3),
            Program(name='Software Engineering', code='SE', duration_years=4),
            Program(name='Information Technology', code='IT', duration_years=3),
            Program(name='Data Science', code='DS', duration_years=3),
        ]
        db.session.add_all(programs)
        db.session.commit()
        
        print("✅ Creating Courses...")
        courses = [
            Course(code='CS101', name='Introduction to Programming', program_id=1, credits=3, semester=1),
            Course(code='CS102', name='Data Structures', program_id=1, credits=3, semester=2),
            Course(code='BA101', name='Business Fundamentals', program_id=2, credits=3, semester=1),
            Course(code='SE101', name='Software Development Basics', program_id=3, credits=3, semester=1),
            Course(code='IT101', name='IT Fundamentals', program_id=4, credits=3, semester=1),
            Course(code='DS101', name='Data Analysis Basics', program_id=5, credits=3, semester=1),
        ]
        db.session.add_all(courses)
        db.session.commit()
        
        print("✅ Creating Accommodations...")
        accommodations = [
            Accommodation(
                name='North Campus Residence',
                address='123 University Ave',
                capacity=200,
                available_rooms=45,
                price_per_semester=1500.0,
                amenities='WiFi, Laundry, Cafeteria, Security'
            ),
            Accommodation(
                name='South Campus Dorms',
                address='456 College St',
                capacity=150,
                available_rooms=30,
                price_per_semester=1200.0,
                amenities='WiFi, Study Rooms, Gym'
            ),
            Accommodation(
                name='East Wing Apartments',
                address='789 Student Blvd',
                capacity=100,
                available_rooms=15,
                price_per_semester=1800.0,
                amenities='WiFi, Furnished, Kitchen, Parking'
            ),
        ]
        db.session.add_all(accommodations)
        db.session.commit()
        
        print("✅ Creating Sample User...")
        user = User(
            email='student@gipscollege.edu',
            password_hash=generate_password_hash('Password123'),
            first_name='Test',
            last_name='Student',
            phone='+267 71234567',
            role='student',
            is_active=True,
            email_verified=True
        )
        db.session.add(user)
        db.session.commit()
        
        print("✅ Creating Sample Student...")
        student = Student(
            user_id=user.id,
            student_number='STU001',
            program_id=1,
            status='active',
            gpa=3.5
        )
        db.session.add(student)
        db.session.commit()
        
        print("✅ Creating Sample Assignment...")
        assignment = Assignment(
            course_id=1,
            title='Assignment 1: Variables',
            description='Complete 10 programming exercises',
            due_date=datetime.utcnow() + timedelta(days=7),
            max_score=100
        )
        db.session.add(assignment)
        db.session.commit()
        
        print("\n✅ Database seeded successfully!")
        print(f"📊 Sample credentials:")
        print(f"   Email: student@gipscollege.edu")
        print(f"   Password: Password123")

if __name__ == '__main__':
    seed_database()