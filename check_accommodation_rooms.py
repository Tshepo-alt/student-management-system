#!/usr/bin/env python3
"""
Check and populate accommodation rooms in the database.
Run: python check_accommodation_rooms.py
"""

import os
import sys
from pathlib import Path

# Add project root to path so we can import models
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config import config
from models import db, Campus, AccommodationRoom

def create_app():
    """Minimal Flask app to run DB queries."""
    env = os.getenv('FLASK_ENV', 'development')
    app = Flask(__name__)
    app.config.from_object(config[env])
    # Use the same DATABASE_URL as your main app
    db.init_app(app)
    return app

def check_rooms():
    """Count existing rooms and display summary."""
    campuses = Campus.query.all()
    if not campuses:
        print("❌ No campuses found in database. Please add campuses first.")
        return False

    print("\n📊 Current accommodation rooms summary:")
    rooms = AccommodationRoom.query.all()
    if not rooms:
        print("   ⚠️ No rooms found at all.")
        return False

    # Group by block and type
    blocks = {}
    for r in rooms:
        key = (r.block_name, r.room_type)
        if key not in blocks:
            blocks[key] = {'available': 0, 'total': 0}
        blocks[key]['total'] += 1
        if r.is_available:
            blocks[key]['available'] += 1

    for (block, rtype), stats in blocks.items():
        print(f"   Block {block} - {rtype.replace('_', ' ').title()}: {stats['available']}/{stats['total']} available")
    return True

def insert_sample_rooms():
    """Insert sample rooms if none exist."""
    print("\n🏠 No rooms found. Do you want to insert sample rooms for testing?")
    choice = input("Type 'yes' to insert sample rooms: ").strip().lower()
    if choice != 'yes':
        print("Aborted.")
        return False

    # Get campuses that have accommodation
    campuses = Campus.query.filter_by(has_accommodation=True).all()
    if not campuses:
        print("❌ No campus with has_accommodation=True found. Please enable accommodation for a campus first.")
        return False

    print(f"Found {len(campuses)} campus(es) with accommodation: {[c.campus_name for c in campuses]}")

    # Predefined rooms for each campus
    rooms_to_insert = []

    # For each campus, create a set of rooms (different blocks)
    for campus in campuses:
        # Use campus code as part of block name? We'll just use generic block names.
        blocks = ['A', 'B', 'C']
        for block in blocks:
            # Bachelor pads: rooms 101-105
            for i in range(1, 6):
                rooms_to_insert.append({
                    'block_name': f"{campus.campus_code}-{block}",
                    'room_number': f"{block}01{i}",
                    'room_type': 'bachelor_pad',
                    'capacity': 1,
                    'current_occupants': 0,
                    'has_kitchen': True,
                    'has_shower': True,
                    'has_study_table': True,
                    'has_bed': True,
                    'is_available': True
                })
            # Three‑bed rooms: 201-205
            for i in range(1, 6):
                rooms_to_insert.append({
                    'block_name': f"{campus.campus_code}-{block}",
                    'room_number': f"{block}02{i}",
                    'room_type': 'three_bed',
                    'capacity': 3,
                    'current_occupants': 0,
                    'has_kitchen': True,
                    'has_shower': True,
                    'has_study_table': True,
                    'has_bed': True,
                    'is_available': True
                })

    # Insert all rooms
    for room_data in rooms_to_insert:
        room = AccommodationRoom(**room_data)
        db.session.add(room)

    db.session.commit()
    print(f"✅ Inserted {len(rooms_to_insert)} sample rooms.")
    return True

def main():
    app = create_app()
    with app.app_context():
        print("\n🔍 Checking accommodation rooms...")
        has_rooms = check_rooms()
        if not has_rooms:
            inserted = insert_sample_rooms()
            if inserted:
                print("\n✅ Rooms have been added. You can now apply for accommodation.")
                # Show updated summary
                check_rooms()
            else:
                print("\n⚠️ No rooms added. Please ensure you have at least one campus with `has_accommodation=True` and proper data.")
        else:
            print("\n✅ Rooms already exist. No action needed.")

if __name__ == '__main__':
    main()