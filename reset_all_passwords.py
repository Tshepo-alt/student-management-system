import sys
sys.path.insert(0, 'backend')
from models import db, User
from werkzeug.security import generate_password_hash
from app import create_app

app = create_app()
with app.app_context():
    users_data = [
        ('student@example.com', 'Student123!', 'student'),
        ('admin@gipscollege.edu.bw', 'Admin@2026!', 'admin'),
        ('registrar@gipscollege.edu.bw', 'Registrar@2026!', 'registrar'),
        ('finance@gipscollege.edu.bw', 'Finance@2026!', 'finance'),
        ('accommodation@gipscollege.edu.bw', 'Staff@2026!', 'staff'),
        ('lecturer@example.com', 'Lecturer@2026!', 'lecturer'),
        ('alumni@example.com', 'Alumni@2026!', 'alumni'),
    ]
    for email, password, role in users_data:
        user = User.query.filter_by(email=email).first()
        if user:
            user.password_hash = generate_password_hash(password)
            if user.role != role:
                user.role = role
            print(f"Updated {email} (role: {user.role})")
        else:
            print(f"User {email} not found")
    db.session.commit()
    print("All users updated.")