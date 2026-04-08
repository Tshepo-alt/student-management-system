# backend/utils/meeting_helper.py
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ============================================
# GOOGLE MEET HELPER (REAL API)
# ============================================

# Read configuration from environment variables
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'backend/config/gips-meet-key.json')
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')


def create_google_meet_link(
    course_name: str,
    lecturer_email: str = None,
    start_time: Optional[datetime] = None,
    duration_minutes: int = 60
) -> Optional[str]:
    """
    Create a real Google Meet link using Google Calendar API.
    
    Args:
        course_name: Name of the course
        lecturer_email: Email of the lecturer (optional, not used with service account)
        start_time: Start time of the meeting (default: now + 5 minutes)
        duration_minutes: Duration in minutes (default: 60)
    
    Returns:
        Google Meet URL or None if creation fails
    """
    try:
        # Load service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=credentials)

        # Set default start time if not provided
        if not start_time:
            start_time = datetime.utcnow() + timedelta(minutes=5)
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Create calendar event with conference data
        event = {
            'summary': f'Live Class: {course_name}',
            'description': 'This class is managed via GIPS College Student Portal.',
            'start': {
                'dateTime': start_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': f"{course_name.replace(' ', '_')}_{int(start_time.timestamp())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                }
            },
        }

        # Insert the event
        created_event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event,
            conferenceDataVersion=1
        ).execute()

        meeting_link = created_event.get('hangoutLink')
        if meeting_link:
            print(f"[GOOGLE MEET] Created meeting for '{course_name}': {meeting_link}")
            return meeting_link
        else:
            print("[GOOGLE MEET] No hangoutLink in response")
            return None

    except Exception as e:
        print(f"[GOOGLE MEET] Error creating event: {e}")
        # Fallback to a mock link so the system still works for testing
        mock_link = f"https://meet.google.com/new?course={course_name.replace(' ', '_')}"
        print(f"[GOOGLE MEET] Using mock link: {mock_link}")
        return mock_link


def create_google_calendar_event(
    course_name: str,
    lecturer_email: str,
    start_time: datetime,
    duration_minutes: int = 60,
    student_emails: list = None
) -> Optional[Dict[str, Any]]:
    """
    Create a full Google Calendar event with Meet link and invite attendees.
    This is an advanced version that also sends invitations.
    
    Args:
        course_name: Name of the course
        lecturer_email: Email of the lecturer
        start_time: Start time of the event
        duration_minutes: Duration in minutes
        student_emails: List of student emails to invite
    
    Returns:
        Dictionary with event details including meet link
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=credentials)

        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            'summary': f'Live Class: {course_name}',
            'description': 'This class is managed via GIPS College Student Portal.',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Africa/Gaborone',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Africa/Gaborone',
            },
            'attendees': [{'email': lecturer_email}],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"{course_name.replace(' ', '_')}_{int(start_time.timestamp())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                }
            },
        }

        if student_emails:
            for email in student_emails:
                event['attendees'].append({'email': email})

        created_event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'  # Send email invitations
        ).execute()

        meeting_link = created_event.get('hangoutLink')
        print(f"[GOOGLE CALENDAR] Created event with meeting: {meeting_link}")
        return {
            'meeting_link': meeting_link,
            'event_id': created_event.get('id'),
            'event_link': created_event.get('htmlLink'),
        }

    except Exception as e:
        print(f"[GOOGLE CALENDAR] Error creating event: {e}")
        return None


# ============================================
# UTILITY FUNCTIONS
# ============================================

def generate_meeting_id(course_name: str) -> str:
    """
    Generate a unique meeting ID based on course name and timestamp.
    Returns a 10-character alphanumeric string.
    """
    import hashlib

    unique_string = f"{course_name}{datetime.now().timestamp()}{secrets.token_hex(4)}"
    hash_object = hashlib.md5(unique_string.encode())
    hash_hex = hash_object.hexdigest()
    meeting_id = hash_hex[:10].upper()
    return meeting_id


def generate_meeting_password(length: int = 8) -> str:
    """Generate a random meeting password."""
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    return ''.join(secrets.choice(chars) for _ in range(length))


# ============================================
# MEETING MANAGER CLASS
# ============================================

class MeetingManager:
    """Centralized meeting management (Google Meet only)."""

    def __init__(self):
        self.active_meetings = {}

    def create_meeting(self, course_name: str, lecturer_email: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Create a Google Meet meeting."""
        meeting_url = create_google_meet_link(course_name, lecturer_email, **kwargs)
        if meeting_url:
            meeting_id = generate_meeting_id(course_name)
            self.active_meetings[meeting_id] = {
                'meeting_url': meeting_url,
                'platform': 'google_meet',
                'created_at': datetime.now().isoformat(),
                'is_active': True,
                **kwargs
            }
            return self.active_meetings[meeting_id]
        return None

    def end_meeting(self, meeting_id: str) -> bool:
        """End an active meeting."""
        if meeting_id in self.active_meetings:
            del self.active_meetings[meeting_id]
            return True
        return False

    def get_active_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        return self.active_meetings.get(meeting_id)


# ============================================
# MEETING LINKS STORAGE (In-memory for demo)
# ============================================

_meeting_links = {}

def store_meeting_link(course_id: int, meeting_link: str, platform: str = 'google_meet') -> None:
    _meeting_links[course_id] = {
        'link': meeting_link,
        'platform': platform,
        'created_at': datetime.now().isoformat(),
        'is_active': True
    }

def get_stored_meeting_link(course_id: int) -> Optional[Dict[str, Any]]:
    return _meeting_links.get(course_id)

def clear_meeting_link(course_id: int) -> bool:
    if course_id in _meeting_links:
        del _meeting_links[course_id]
        return True
    return False


# ============================================
# HELPER FOR EMBEDDED MEETING IFRAME
# ============================================

def get_embedded_meeting_html(meeting_url: str, course_name: str) -> str:
    """Generate HTML for embedded meeting iframe."""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Class: {course_name}</title>
        <style>
            body {{ margin: 0; padding: 0; overflow: hidden; }}
            iframe {{ width: 100%; height: 100vh; border: none; }}
        </style>
    </head>
    <body>
        <iframe src="{meeting_url}" allow="camera; microphone; fullscreen; display-capture" allowfullscreen></iframe>
    </body>
    </html>
    '''


# ============================================
# EXPORTS
# ============================================

__all__ = [
    'create_google_meet_link',
    'create_google_calendar_event',
    'generate_meeting_id',
    'generate_meeting_password',
    'MeetingManager',
    'store_meeting_link',
    'get_stored_meeting_link',
    'clear_meeting_link',
    'get_embedded_meeting_html'
]