# create_masego_admin.py
import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models import db, User, Student
from werkzeug.security import generate_password_hash
from datetime import datetime

# Create Flask app context manually
from flask import Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Admin@localhost:3306/gips_college_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def create_masego_admin():
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email='masego@gipscollege.com').first()
        
        if existing_user:
            print("=" * 60)
            print("⚠️  USER ALREADY EXISTS!")
            print("=" * 60)
            print(f"Email: {existing_user.email}")
            print(f"Username: {existing_user.username}")
            print(f"Role: {existing_user.role}")
            print("=" * 60)
            return
        
        # Create the admin user
        admin_user = User(
            username='masego_admin',
            email='masego@gipscollege.com',
            password_hash=generate_password_hash('Masego@2026!'),
            role='admin',
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(admin_user)
        db.session.flush()
        
        # Create a student record for admin (optional but recommended)
        admin_student = Student(
            user_id=admin_user.id,
            student_number='ADMIN_MASEGO',
            first_name='Masego',
            last_name='Administrator',
            email='masego@gipscollege.com',
            phone='+267 71234567',
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(admin_student)
        db.session.commit()
        
        print("=" * 60)
        print("✅ ADMIN USER CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Email: masego@gipscollege.com")
        print(f"Password: Masego@2026!")
        print(f"Username: masego_admin")
        print(f"Role: admin")
        print("=" * 60)
        print("\n🎉 You can now log in at: http://localhost:5000/pages/login.html")
        print("📧 Use the credentials above to access the admin dashboard.")
        print("🔑 Password: Masego@2026!")
        print("=" * 60)

if __name__ == '__main__':
    create_masego_admin()