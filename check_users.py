#!/usr/bin/env python3
"""
Check users and their roles in the database.
Run: python check_users.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config import config
from models import db, User, Student, UserRole, Role

def create_app():
    env = os.getenv('FLASK_ENV', 'development')
    app = Flask(__name__)
    app.config.from_object(config[env])
    db.init_app(app)
    return app

def main():
    app = create_app()
    with app.app_context():
        print("\n" + "="*80)
        print("USERS & ROLES IN DATABASE")
        print("="*80)

        users = User.query.order_by(User.id).all()
        if not users:
            print("No users found.")
            return

        print(f"\n{'ID':<4} {'Username':<20} {'Email':<30} {'Role (direct)':<15} {'Student #':<15} {'Additional Roles'}")
        print("-" * 100)

        for user in users:
            student = Student.query.filter_by(user_id=user.id).first()
            student_num = student.student_number if student else "N/A"
            # Get additional roles from user_roles
            extra_roles = [ur.role.role_name for ur in user.user_roles if ur.role]
            extra_str = ", ".join(extra_roles) if extra_roles else "-"

            print(f"{user.id:<4} {user.username:<20} {user.email:<30} {user.role:<15} {student_num:<15} {extra_str}")

        # Also show roles table if any (for reference)
        print("\n" + "="*80)
        print("AVAILABLE ROLES (from roles table)")
        print("="*80)
        roles = Role.query.all()
        if roles:
            for r in roles:
                print(f"  {r.role_name} - {r.description or 'No description'}")
        else:
            print("  No roles defined in 'roles' table (only direct 'role' column used).")
        print("")

if __name__ == '__main__':
    main()