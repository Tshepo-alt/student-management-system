#!/usr/bin/env python3
"""
Setup accommodation: create campus (if missing) and insert sample rooms.
Run: python setup_accommodation.py
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config import config
from models import db, Campus, AccommodationRoom

def create_app():
    env = os.getenv('FLASK_ENV', 'development')
    app = Flask(__name__)
    app.config.from_object(config[env])
    db.init_app(app)
    return app

def main():
    app = create_app()
    with app.app_context():
        print("\n🏫 Checking campuses...")
        campuses = Campus.query.all()
        if not campuses:
            print("No campus found. Creating Gaborone Main Campus...")
            campus = Campus(
                campus_code="GAB",
                campus_name="Gaborone Main Campus",
                campus_location="Gaborone, Botswana",
                has_accommodation=True,
                is_main_campus=True
            )
            db.session.add(campus)
            db.session.commit()
            print("✅ Campus created:", campus.campus_name)
        else:
            # Use the first campus (or pick one with accommodation)
            campus = next((c for c in campuses if c.has_accommodation), campuses[0])
            if not campus.has_accommodation:
                print(f"⚠️ Campus {campus.campus_name} has accommodation disabled. Enabling it.")
                campus.has_accommodation = True
                db.session.commit()
            print(f"✅ Using campus: {campus.campus_name} (has_accommodation={campus.has_accommodation})")

        # Now check rooms
        rooms = AccommodationRoom.query.all()
        if rooms:
            print(f"\n✅ Rooms already exist ({len(rooms)} found). No action needed.")
            # Show summary
            for block, rtype in set((r.block_name, r.room_type) for r in rooms):
                avail = AccommodationRoom.query.filter_by(block_name=block, room_type=rtype, is_available=True).count()
                total = AccommodationRoom.query.filter_by(block_name=block, room_type=rtype).count()
                print(f"   Block {block} - {rtype.replace('_',' ').title()}: {avail}/{total} available")
            return

        print("\n🏠 No rooms found. Creating sample rooms for the campus...")
        campus = Campus.query.filter_by(has_accommodation=True).first()
        if not campus:
            print("❌ No campus with accommodation enabled. Please set has_accommodation=True for a campus first.")
            return

        blocks = ['A', 'B', 'C']
        room_count = 0
        for block in blocks:
            block_name = f"{campus.campus_code}-{block}"  # e.g., GAB-A
            # Bachelor pads (1 person)
            for num in range(1, 6):
                room = AccommodationRoom(
                    block_name=block_name,
                    room_number=f"{block}01{num}",
                    room_type='bachelor_pad',
                    capacity=1,
                    current_occupants=0,
                    has_kitchen=True,
                    has_shower=True,
                    has_study_table=True,
                    has_bed=True,
                    is_available=True
                )
                db.session.add(room)
                room_count += 1
            # Three‑bed rooms (3 persons)
            for num in range(1, 6):
                room = AccommodationRoom(
                    block_name=block_name,
                    room_number=f"{block}02{num}",
                    room_type='three_bed',
                    capacity=3,
                    current_occupants=0,
                    has_kitchen=True,
                    has_shower=True,
                    has_study_table=True,
                    has_bed=True,
                    is_available=True
                )
                db.session.add(room)
                room_count += 1

        db.session.commit()
        print(f"✅ Inserted {room_count} sample rooms (bachelor pads + three‑bed) for campus {campus.campus_name}.")
        print("You can now apply for accommodation.")

if __name__ == '__main__':
    main()