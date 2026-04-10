# backend/routes/chatbot_routes.py
import os
import re
import logging
import traceback
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from flask_jwt_extended import jwt_required, get_jwt_identity
from openai import OpenAI

# Import all necessary models for data fetching
from models import (
    User, Student, Enrollment, Module, Registration, Payment,
    AccommodationRegistration, AccommodationRoom, AcademicYear, Semester,
    Program, Campus
)

chatbot_bp = Blueprint('samantha', __name__)
logger = logging.getLogger(__name__)

# ============================================
# SMS DATA INTEGRATION LAYER (UPGRADE)
# ============================================

def get_student_results(student_id):
    """
    Fetch the student's recent academic results (enrollments with grades).
    Returns a formatted string of modules and grades.
    """
    try:
        enrollments = Enrollment.query.filter_by(student_id=student_id)\
            .filter(Enrollment.grade.isnot(None))\
            .order_by(Enrollment.created_at.desc())\
            .limit(15).all()
        
        if not enrollments:
            return "No academic results found for this student."
        
        result_lines = ["Your recent academic results:"]
        for e in enrollments:
            module = Module.query.get(e.module_id)
            module_name = module.module_name if module else "Unknown Module"
            grade = e.grade or "IP"  # In Progress
            result_lines.append(f"• {module_name}: {grade}")
        
        return "\n".join(result_lines)
    except Exception as e:
        logger.error(f"Error fetching student results: {e}")
        return "Unable to retrieve academic results at this moment."

def get_student_finances(student_id):
    """
    Fetch the student's current fee balance from the latest registration.
    Returns balance, paid amount, and total fees.
    """
    try:
        # Get the most recent registration for this student
        registration = Registration.query.filter_by(student_id=student_id)\
            .order_by(Registration.created_at.desc()).first()
        
        if not registration:
            return "No financial records found for this student."
        
        total = float(registration.total_fees or 0)
        paid = float(registration.paid_amount or 0)
        exempt = float(registration.exempted_amount or 0)
        balance = total - paid - exempt
        
        # Determine sponsorship status
        student = Student.query.get(student_id)
        sponsored = student.is_government_sponsored if student else False
        
        academic_year_name = registration.academic_year.year_name if registration.academic_year else "Current Year"
        
        response = f"**Fee Summary for {academic_year_name}**\n"
        response += f"Total Fees: P{total:,.2f}\n"
        response += f"Paid: P{paid:,.2f}\n"
        if exempt > 0:
            response += f"Exempted (Govt): P{exempt:,.2f}\n"
        response += f"Outstanding Balance: P{balance:,.2f}\n"
        
        if sponsored:
            response += "\nNote: You are government sponsored. Eligible fees are covered."
        
        return response
    except Exception as e:
        logger.error(f"Error fetching student finances: {e}")
        return "Unable to retrieve financial information at this moment."

def get_student_accommodation(student_id):
    """
    Fetch the student's current accommodation allocation.
    """
    try:
        # Find active accommodation registration
        acc_reg = AccommodationRegistration.query.filter_by(student_id=student_id)\
            .filter(AccommodationRegistration.status.in_(['approved', 'allocated']))\
            .order_by(AccommodationRegistration.created_at.desc()).first()
        
        if not acc_reg:
            return "You do not have an active accommodation allocation. To apply, please visit the Accommodation portal."
        
        room = None
        if acc_reg.allocated_room_id:
            room = AccommodationRoom.query.get(acc_reg.allocated_room_id)
        
        response = "**Accommodation Details**\n"
        response += f"Status: {acc_reg.status.capitalize()}\n"
        
        if room:
            response += f"Block: {room.block_name}\n"
            response += f"Room: {room.room_number}\n"
            response += f"Room Type: {room.room_type.replace('_', ' ').title()}\n"
        else:
            response += "Allocation: Pending room assignment\n"
        
        if acc_reg.check_in_date:
            response += f"Check-in Date: {acc_reg.check_in_date.strftime('%d %B %Y')}\n"
        if acc_reg.check_out_date:
            response += f"Check-out Date: {acc_reg.check_out_date.strftime('%d %B %Y')}\n"
        
        return response
    except Exception as e:
        logger.error(f"Error fetching accommodation: {e}")
        return "Unable to retrieve accommodation details at this moment."

def get_student_timetable(student_id):
    """
    Fetch the student's current semester timetable.
    Since timetable data may be stored elsewhere, this returns a placeholder with a link.
    """
    try:
        student = Student.query.get(student_id)
        if not student:
            return "Student record not found."
        
        # In a full implementation, you would query a timetable table.
        # For now, direct to the portal.
        return f"Your current timetable for Year {student.current_year} is available on the Student Portal under 'My Courses'. You can view your registered courses and meeting schedules there."
    except Exception as e:
        logger.error(f"Error fetching timetable: {e}")
        return "Unable to retrieve timetable information."


# ============================================
# ADVANCED AI ENGINE (OPENAI POWERED)
# ============================================

class SamanthaAIEngine:
    """AI engine using OpenAI GPT for intelligent, context-aware responses."""

    def __init__(self):
        self.conversations = {}          # user_id -> conversation context
        self.user_preferences = {}       # user_id -> preferences
        self.use_ai = None               # will be set from env on first call
        self.openai_client = None        # lazy initialization
        self.api_key = None

    def _get_openai_client(self):
        """Initialize OpenAI client with the key from environment."""
        if self.openai_client is None:
            api_key = os.environ.get('CHATBOT_OPENAI_API_KEY')
            if not api_key:
                logger.error("OpenAI API key not found in environment")
                self.use_ai = False
                return None
            self.api_key = api_key
            self.openai_client = OpenAI(api_key=api_key)
        return self.openai_client

    def get_context(self, user_id):
        """Get or create conversation context for a user."""
        uid = str(user_id)
        if uid not in self.conversations:
            self.conversations[uid] = {
                'history': [],           # list of {role: user/assistant, content: ...}
                'last_topic': None,
                'user_name': None,
                'student_info': None,
                'preferences': {}
            }
        return self.conversations[uid]

    def update_context(self, user_id, message, response, topic=None):
        """Add a turn to the conversation history."""
        uid = str(user_id)
        ctx = self.get_context(uid)
        ctx['history'].append({'role': 'user', 'content': message})
        ctx['history'].append({'role': 'assistant', 'content': response})
        if topic:
            ctx['last_topic'] = topic
        # Keep only the last 20 messages to avoid token overflow
        if len(ctx['history']) > 20:
            ctx['history'] = ctx['history'][-20:]

    def detect_intent(self, message):
        """Simple rule‑based intent detection for analytics (optional)."""
        msg_lower = message.lower()
        intents = {
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'howdy'],
            'farewell': ['bye', 'goodbye', 'see you', 'thanks bye', 'talk later'],
            'course_registration': ['register', 'course registration', 'enroll', 'add course'],
            'fee_payment': ['pay', 'payment', 'fee', 'tuition', 'cost', 'balance', 'owe'],
            'career_guidance': ['career', 'job', 'work', 'employment', 'salary'],
            'market_insights': ['market', 'economy', 'business', 'trend', 'industry'],
            'academic_help': ['assignment', 'homework', 'study', 'exam', 'test', 'help with', 'explain', 'essay'],
            'ticket_support': ['ticket', 'issue', 'problem', 'help', 'support', 'complaint'],
            'personal_info': ['who are you', 'what can you do', 'capabilities', 'about you'],
            'emotional': ['sad', 'stressed', 'worried', 'anxious', 'overwhelmed', 'happy', 'excited'],
            'accommodation': ['accommodation', 'hostel', 'room', 'housing', 'residence'],
            'exam_results': ['result', 'grade', 'score', 'marks', 'gpa', 'transcript'],
            'library': ['library', 'book', 'borrow', 'resource'],
            'deadlines': ['deadline', 'due date', 'when is']
        }
        for intent, keywords in intents.items():
            if any(keyword in msg_lower for keyword in keywords):
                return intent
        return 'general'

    def extract_name(self, message):
        """Extract user name from a greeting message."""
        patterns = [
            r'my name is (\w+)',
            r"i'm (\w+)",
            r'i am (\w+)',
            r'call me (\w+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1).capitalize()
        return None

    def _build_system_prompt(self, user_context, student_info):
        """Build a detailed system prompt with college context and user info."""
        name = user_context.get('user_name', 'Student')
        if student_info:
            # Use the student's real first name if available
            student = Student.query.get(student_info.get('id'))
            if student:
                name = student.first_name
        
        prompt = f"""You are Samantha, a friendly, knowledgeable, and professional AI assistant for GIPS College in Gaborone, Botswana. Your role is to help students with academic, financial, accommodation, and general college-related queries.

**Language Instruction:**
- If the user writes in Setswana, you MUST respond in Setswana.
- If the user writes in English, respond in English.
- Use a warm, respectful tone appropriate for Botswana culture.

**Important College Information:**
- College: GIPS College, Gaborone, Botswana
- Website: https://www.gipscollege.edu.bw
- Key Contacts:
  * IT Support: it@gipscollege.edu.bw, +267712345678
  * Finance: finance@gipscollege.edu.bw, +267712345680
  * Student Services: studentservices@gipscollege.edu.bw, +267712345681
  * Accommodation: accommodation@gipscollege.edu.bw, +267712345688

**Academic Calendar:**
- Semester 1: July - December
- Semester 2: January - June

**Current User:** {name}
"""
        if student_info:
            prompt += f"\n**Student Details:**\n- Student Number: {student_info.get('student_number', 'N/A')}\n- Program: {student_info.get('program', 'N/A')}\n- Year: {student_info.get('year', 'N/A')}\n"
        
        prompt += """
**Your Personality:**
- Be warm, empathetic, and supportive.
- Provide accurate, helpful information based on the provided data.
- If you don't know something, suggest contacting the appropriate department.
- Keep responses concise but thorough.
"""
        return prompt

    def _call_openai(self, messages, model="gpt-3.5-turbo", max_tokens=500):
        """Call OpenAI API and return the assistant's reply."""
        client = self._get_openai_client()
        if not client:
            return "I'm sorry, the AI service is currently unavailable. Please try again later."

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm sorry, something went wrong while processing your request. Please try again later."

    def generate_response(self, message, user_context, student_info=None):
        """Generate a response using OpenAI, enhanced with real-time SMS data."""
        
        # Check if AI is enabled from environment
        if self.use_ai is None:
            self.use_ai = os.environ.get('CHATBOT_USE_AI', 'True').lower() == 'true'

        if not self.use_ai:
            return ("I'm sorry, the AI assistant is currently disabled. "
                    "Please contact IT support for assistance.")

        # --- UPGRADE: Fetch Real-Time Data Based on Intent ---
        data_context = ""
        intent = self.detect_intent(message)
        student_id = student_info.get('id') if student_info else None
        msg_lower = message.lower()
        
        if student_id:
            # Results / Grades
            if intent == 'exam_results' or any(kw in msg_lower for kw in ['result', 'grade', 'marks', 'gpa']):
                data_context = get_student_results(student_id)
            
            # Fees / Balance
            elif intent == 'fee_payment' or any(kw in msg_lower for kw in ['balance', 'owe', 'fees', 'payment', 'tuition']):
                data_context = get_student_finances(student_id)
            
            # Accommodation
            elif intent == 'accommodation' or any(kw in msg_lower for kw in ['room', 'hostel', 'residence', 'accommodation']):
                data_context = get_student_accommodation(student_id)
            
            # Timetable / Schedule
            elif any(kw in msg_lower for kw in ['timetable', 'schedule', 'classes', 'lecture']):
                data_context = get_student_timetable(student_id)

        # Build conversation messages
        messages = []
        system_prompt = self._build_system_prompt(user_context, student_info)
        
        # Inject real-time data if available
        if data_context:
            system_prompt += f"\n\n**REAL-TIME STUDENT DATA (Use this precise information to answer):**\n{data_context}"
            system_prompt += "\n\nImportant: Use the above data to provide an accurate, personalized response. Do not invent numbers."
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add recent conversation history (up to 10 turns)
        history = user_context.get('history', [])
        for entry in history[-10:]:
            messages.append({"role": entry['role'], "content": entry['content']})
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Call OpenAI
        response = self._call_openai(messages)
        
        # Update context for analytics
        self.update_context(user_context.get('user_id'), message, response, intent)
        
        return response


# ============================================
# INITIALIZE SAMANTHA AI ENGINE
# ============================================
samantha_engine = SamanthaAIEngine()

# ============================================
# HELPER FUNCTIONS
# ============================================
def get_user_from_token():
    """Get user from JWT token or session."""
    try:
        from models import User, Student
        from flask_jwt_extended import get_jwt_identity
        try:
            user_id = get_jwt_identity()
            if user_id:
                return User.query.get(user_id)
        except:
            pass
        if current_user.is_authenticated:
            return current_user
        return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

# ============================================
# API ENDPOINTS
# ============================================

@chatbot_bp.route('/message', methods=['POST'])
def process_message():
    """Process user message and return AI response."""
    try:
        user = get_user_from_token()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.json
        message = data.get('message', '').strip()
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Get student info if exists
        student_info = None
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            student_info = {
                'id': student.id,
                'student_number': student.student_number,
                'program': student.program.program_name if student.program else None,
                'year': student.current_year
            }

        context = samantha_engine.get_context(user.id)
        # Ensure user_id is stored in context for history management
        context['user_id'] = user.id

        # Extract name from message if not already known
        if not context.get('user_name'):
            extracted_name = samantha_engine.extract_name(message)
            if extracted_name:
                context['user_name'] = extracted_name
            elif student and student.first_name:
                context['user_name'] = student.first_name

        # Generate response
        response = samantha_engine.generate_response(message, context, student_info)
        intent = samantha_engine.detect_intent(message)

        return jsonify({
            'success': True,
            'response': response,
            'intent': intent,
            'context': {'history_length': len(context['history'])}
        }), 200

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/voice', methods=['POST'])
def process_voice():
    """Process voice input (transcript) and return AI response."""
    try:
        user = get_user_from_token()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.json
        transcript = data.get('transcript', '').strip()
        if not transcript:
            return jsonify({'error': 'Voice transcript required'}), 400

        # Get student info
        student_info = None
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            student_info = {
                'id': student.id,
                'student_number': student.student_number,
                'program': student.program.program_name if student.program else None,
                'year': student.current_year
            }

        context = samantha_engine.get_context(user.id)
        context['user_id'] = user.id

        response = samantha_engine.generate_response(transcript, context, student_info)
        intent = samantha_engine.detect_intent(transcript)

        return jsonify({
            'success': True,
            'response': response,
            'intent': intent
        }), 200

    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/context', methods=['GET'])
def get_context():
    """Return the user's conversation history."""
    try:
        user = get_user_from_token()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        context = samantha_engine.get_context(user.id)
        return jsonify({
            'success': True,
            'data': {
                'history': context.get('history', [])[-10:],
                'last_topic': context.get('last_topic'),
                'user_name': context.get('user_name')
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/context/reset', methods=['POST'])
def reset_context():
    """Reset the user's conversation context."""
    try:
        user = get_user_from_token()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        uid = str(user.id)
        user_name = samantha_engine.get_context(user.id).get('user_name')
        samantha_engine.conversations[uid] = {
            'history': [],
            'last_topic': None,
            'user_name': user_name,
            'student_info': None,
            'preferences': {}
        }
        return jsonify({'success': True, 'message': 'Context reset successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/ticket/<int:ticket_id>', methods=['GET'])
def get_ticket_status(ticket_id):
    """Get the status of a specific support ticket."""
    try:
        user = get_user_from_token()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        # Placeholder – replace with actual database lookup
        return jsonify({
            'success': True,
            'ticket': {
                'id': ticket_id,
                'status': 'open',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/tickets', methods=['GET'])
def get_my_tickets():
    """Get all tickets for the current user."""
    try:
        user = get_user_from_token()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        # Placeholder – replace with actual database query
        return jsonify({
            'success': True,
            'tickets': []
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chatbot_bp.route('/health', methods=['GET'])
def chatbot_health():
    """Health check endpoint."""
    try:
        return jsonify({
            'status': 'healthy',
            'engine': 'Samantha AI v4.0 (OpenAI + SMS Integration)',
            'ai_enabled': samantha_engine.use_ai,
            'features': [
                'voice_conversations',
                'context_memory',
                'intent_recognition',
                'sentiment_detection',
                'academic_help',
                'career_guidance',
                'market_insights',
                'ticket_support',
                'openai_integration',
                'real_time_results',
                'real_time_finance',
                'real_time_accommodation',
                'setswana_support'
            ]
        }), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500