#!/usr/bin/env python
"""
Insert accommodation rooms into the Aiven MySQL database.
Run this script locally or on Render Shell.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables from .env if present (for local)
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from app import create_app
from models import db, AccommodationRoom

# Define all rooms (block A to E, with appropriate room numbers and types)
# Adjust according to your actual campus layout
ROOMS_DATA = [
    # Block A - Bachelor Pads (rooms 101-104)
    {"block": "A", "number": "101", "type": "bachelor_pad", "capacity": 2},
    {"block": "A", "number": "102", "type": "bachelor_pad", "capacity": 2},
    {"block": "A", "number": "103", "type": "bachelor_pad", "capacity": 2},
    {"block": "A", "number": "104", "type": "bachelor_pad", "capacity": 2},
    # Block A - Three-Bed Rooms (rooms 201-204)
    {"block": "A", "number": "201", "type": "three_bed", "capacity": 6},
    {"block": "A", "number": "202", "type": "three_bed", "capacity": 6},
    {"block": "A", "number": "203", "type": "three_bed", "capacity": 6},
    {"block": "A", "number": "204", "type": "three_bed", "capacity": 6},
    
    # Block B
    {"block": "B", "number": "101", "type": "bachelor_pad", "capacity": 2},
    {"block": "B", "number": "102", "type": "bachelor_pad", "capacity": 2},
    {"block": "B", "number": "103", "type": "bachelor_pad", "capacity": 2},
    {"block": "B", "number": "104", "type": "bachelor_pad", "capacity": 2},
    {"block": "B", "number": "201", "type": "three_bed", "capacity": 6},
    {"block": "B", "number": "202", "type": "three_bed", "capacity": 6},
    {"block": "B", "number": "203", "type": "three_bed", "capacity": 6},
    {"block": "B", "number": "204", "type": "three_bed", "capacity": 6},
    
    # Block C
    {"block": "C", "number": "101", "type": "bachelor_pad", "capacity": 2},
    {"block": "C", "number": "102", "type": "bachelor_pad", "capacity": 2},
    {"block": "C", "number": "103", "type": "bachelor_pad", "capacity": 2},
    {"block": "C", "number": "104", "type": "bachelor_pad", "capacity": 2},
    {"block": "C", "number": "201", "type": "three_bed", "capacity": 6},
    {"block": "C", "number": "202", "type": "three_bed", "capacity": 6},
    {"block": "C", "number": "203", "type": "three_bed", "capacity": 6},
    {"block": "C", "number": "204", "type": "three_bed", "capacity": 6},
    
    # Block D
    {"block": "D", "number": "101", "type": "bachelor_pad", "capacity": 2},
    {"block": "D", "number": "102", "type": "bachelor_pad", "capacity": 2},
    {"block": "D", "number": "103", "type": "bachelor_pad", "capacity": 2},
    {"block": "D", "number": "104", "type": "bachelor_pad", "capacity": 2},
    {"block": "D", "number": "201", "type": "three_bed", "capacity": 6},
    {"block": "D", "number": "202", "type": "three_bed", "capacity": 6},
    {"block": "D", "number": "203", "type": "three_bed", "capacity": 6},
    {"block": "D", "number": "204", "type": "three_bed", "capacity": 6},
    
    # Block E
    {"block": "E", "number": "101", "type": "bachelor_pad", "capacity": 2},
    {"block": "E", "number": "102", "type": "bachelor_pad", "capacity": 2},
    {"block": "E", "number": "103", "type": "bachelor_pad", "capacity": 2},
    {"block": "E", "number": "104", "type": "bachelor_pad", "capacity": 2},
    {"block": "E", "number": "201", "type": "three_bed", "capacity": 6},
    {"block": "E", "number": "202", "type": "three_bed", "capacity": 6},
    {"block": "E", "number": "203", "type": "three_bed", "capacity": 6},
    {"block": "E", "number": "204", "type": "three_bed", "capacity": 6},
]

def insert_rooms():
    """Insert rooms into database if they don't already exist."""
    app = create_app()
    with app.app_context():
        inserted = 0
        skipped = 0
        
        for room in ROOMS_DATA:
            existing = AccommodationRoom.query.filter_by(
                block_name=room["block"],
                room_number=room["number"]
            ).first()
            
            if existing:
                print(f"⚠️ Room {room['block']}-{room['number']} already exists. Skipping.")
                skipped += 1
                continue
            
            new_room = AccommodationRoom(
                block_name=room["block"],
                room_number=room["number"],
                room_type=room["type"],
                capacity=room["capacity"],
                current_occupants=0,
                is_available=True,          # Available for booking
                has_kitchen=True,
                has_shower=True,
                has_study_table=True,
                has_bed=True
            )
            db.session.add(new_room)
            inserted += 1
        
        if inserted > 0:
            db.session.commit()
            print(f"\n✅ Successfully inserted {inserted} new room(s).")
        else:
            print("\n✅ No new rooms to insert.")
        
        if skipped > 0:
            print(f"⏭️  Skipped {skipped} existing room(s).")
        
        # Show total rooms after insertion
        total = AccommodationRoom.query.count()
        print(f"\n📊 Total rooms in database: {total}")

if __name__ == "__main__":
    print("=" * 60)
    print("🏠 Accommodation Room Inserter")
    print("=" * 60)
    
    # Check if DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable not found.")
        print("   Please set it in your .env file or Render environment.")
        sys.exit(1)
    
    try:
        insert_rooms()
    except Exception as e:
        print(f"\n❌ Error inserting rooms: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)