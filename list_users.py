# list_users.py
import sys
from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    users = User.query.all()
    print("ID | Email | Role")
    print("-" * 50)
    for u in users:
        print(f"{u.id} | {u.email} | {u.role}")