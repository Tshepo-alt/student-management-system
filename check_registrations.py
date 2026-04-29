# check_registrations.py
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config import config
from models import db, Registration

app = Flask(__name__)
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])
db.init_app(app)

with app.app_context():
    all_regs = Registration.query.all()
    print(f"Total registrations: {len(all_regs)}")
    for reg in all_regs:
        print(f"  ID {reg.id} | student_id {reg.student_id} | status {reg.registration_status} | created {reg.created_at}")
    pending = Registration.query.filter_by(registration_status='pending').count()
    print(f"Pending count: {pending}")