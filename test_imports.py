import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from services.moodle_integration import MoodleClient
    print("✅ MoodleClient imported successfully")
except ImportError as e:
    print(f"❌ Failed to import MoodleClient: {e}")

try:
    from config import MOODLE_URL, MOODLE_API_TOKEN
    print(f"✅ MOODLE_URL = {MOODLE_URL}")
    print(f"✅ MOODLE_API_TOKEN = {'[set]' if MOODLE_API_TOKEN else '[empty]'}")
except ImportError as e:
    print(f"❌ Failed to import from config: {e}")

try:
    from backend.routes.students import students_bp
    print("✅ students blueprint imported")
except ImportError as e:
    print(f"❌ Failed to import students blueprint: {e}")
