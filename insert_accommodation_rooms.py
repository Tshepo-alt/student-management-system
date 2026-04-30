# insert_accommodation_rooms.py
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config import config
from models import db, AccommodationRoom, Campus

app = Flask(__name__)
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])
db.init_app(app)

with app.app_context():
    # Ensure campus has accommodation enabled
    campus = Campus.query.filter_by(campus_code='GAB').first()
    if not campus:
        campus = Campus.query.first()
    if campus:
        campus.has_accommodation = True
        db.session.commit()
        print(f"✅ Campus {campus.campus_name} accommodation enabled")
    else:
        print("❌ No campus found. Please create a campus first.")
        exit(1)

    # Clear existing rooms (optional)
    AccommodationRoom.query.delete()
    
    blocks = ['A', 'B', 'C', 'D', 'E']
    rooms_inserted = 0
    for block in blocks:
        block_name = block
        # Bachelor pads (rooms 101-116)
        for i in range(1, 17):  # 16 bachelor pads per block
            room = AccommodationRoom(
                block_name=block_name,
                room_number=f"{block}101{i:02d}" if i<10 else f"{block}101{i}",
                room_type='bachelor_pad',
                capacity=2,
                current_occupants=0,
                is_available=True,
                has_kitchen=True,
                has_shower=True,
                has_study_table=True,
                has_bed=True
            )
            db.session.add(room)
            rooms_inserted += 1
        # Three-bed rooms (rooms 201-216)
        for i in range(1, 17):
            room = AccommodationRoom(
                block_name=block_name,
                room_number=f"{block}201{i:02d}" if i<10 else f"{block}201{i}",
                room_type='three_bed',
                capacity=6,
                current_occupants=0,
                is_available=True,
                has_kitchen=True,
                has_shower=True,
                has_study_table=True,
                has_bed=True
            )
            db.session.add(room)
            rooms_inserted += 1
    db.session.commit()
    print(f"✅ Inserted {rooms_inserted} accommodation rooms (5 blocks × 32 rooms each).")