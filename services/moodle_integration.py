# services/moodle_integration.py
import requests
from typing import List, Dict, Any, Optional

class MoodleClient:
    """Client for Moodle REST API."""

    def __init__(self, moodle_url: str, api_token: str, timeout: int = 30):
        """
        Initialize the Moodle API client.

        :param moodle_url: Base URL of the Moodle site (e.g., https://yourmoodle.com)
        :param api_token: Web service token for authentication
        :param timeout: Request timeout in seconds
        """
        self.moodle_url = moodle_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.endpoint = f"{self.moodle_url}/webservice/rest/server.php"

    def _call(self, wsfunction: str, **params) -> Any:
        """
        Internal method to make a Moodle REST API call.

        :param wsfunction: Name of the web service function
        :param params: Additional parameters to pass to the API
        :return: Parsed JSON response
        :raises requests.RequestException: If the request fails or returns a non-2xx status
        :raises ValueError: If the response indicates a Moodle API error
        """
        payload = {
            'wstoken': self.api_token,
            'wsfunction': wsfunction,
            'moodlewsrestformat': 'json',
            **params
        }
        response = requests.post(self.endpoint, data=payload, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        # Moodle can return an error structure even with 200 OK
        if isinstance(data, dict) and 'exception' in data:
            raise ValueError(f"Moodle API error: {data.get('message', 'Unknown error')}")
        return data

    # ---------- User Management ----------
    def create_user(self, username: str, password: str, firstname: str,
                    lastname: str, email: str) -> int:
        """
        Create a new user in Moodle.

        :return: The newly created user's ID
        """
        result = self._call(
            'core_user_create_users',
            users=[{
                'username': username,
                'password': password,
                'firstname': firstname,
                'lastname': lastname,
                'email': email
            }]
        )
        # Result is a list: [{"id": 123, ...}]
        return result[0]['id']

    def update_user(self, user_id: int, **fields) -> Dict:
        """
        Update an existing user's fields.

        Allowed field keys: firstname, lastname, email, etc.
        """
        return self._call(
            'core_user_update_users',
            users=[{'id': user_id, **fields}]
        )

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Retrieve user details by Moodle user ID."""
        result = self._call('core_user_get_users_by_field', field='id', values=[user_id])
        return result[0] if result else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Retrieve user by email address."""
        result = self._call('core_user_get_users_by_field', field='email', values=[email])
        return result[0] if result else None

    # ---------- Course Management ----------
    def get_courses(self, field: str = None, value: str = None) -> List[Dict]:
        """
        Return a list of courses.
        If field and value are given, filter results (e.g., field='id', value='5').
        """
        params = {}
        if field and value is not None:
            params['field'] = field
            params['value'] = value
        return self._call('core_course_get_courses_by_field', **params)

    def get_course_by_id(self, course_id: int) -> Optional[Dict]:
        """Retrieve a single course by its ID."""
        courses = self.get_courses(field='id', value=str(course_id))
        return courses[0] if courses else None

    def create_course(self, fullname: str, shortname: str,
                      categoryid: int = 1, **extra) -> int:
        """
        Create a new course in Moodle.

        :param fullname: Full course name
        :param shortname: Short course name (e.g., module code)
        :param categoryid: Moodle category ID (default 1)
        :param extra: Additional course parameters (optional)
        :return: The newly created course ID
        """
        course_data = {
            'fullname': fullname,
            'shortname': shortname,
            'categoryid': categoryid,
            **extra
        }
        result = self._call('core_course_create_courses', courses=[course_data])
        return result[0]['id']

    # ---------- Enrolment ----------
    def enrol_user(self, user_id: int, course_id: int, role_id: int = 5) -> None:
        """
        Enrol a user into a course.

        :param role_id: 5 = student, 3 = editing teacher, 4 = non-editing teacher
        """
        self._call(
            'enrol_manual_enrol_users',
            enrolments=[{
                'roleid': role_id,
                'userid': user_id,
                'courseid': course_id
            }]
        )

    # ---------- Grades ----------
    def get_user_grades(self, user_id: int, course_id: int) -> List[Dict]:
        """Get grade items for a user in a specific course."""
        return self._call(
            'gradereport_user_get_grade_items',
            userid=user_id,
            courseid=course_id
        )

    def set_user_grade(self, user_id: int, course_id: int,
                       grade: float, rawgrade: float = None) -> None:
        """
        Set a grade for a user in a Moodle course.

        :param user_id: Moodle user ID
        :param course_id: Moodle course ID
        :param grade: Numeric grade (e.g., 85.5)
        :param rawgrade: Raw points (optional, defaults to grade)
        """
        self._call(
            'gradereport_user_set_grade',
            courseid=course_id,
            userid=user_id,
            grade=grade,
            rawgrade=rawgrade if rawgrade is not None else grade
        )