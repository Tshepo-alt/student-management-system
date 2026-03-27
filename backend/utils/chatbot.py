import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StudentManagementChatbot:
    def __init__(self, app=None, db_path=None, config=None):
        self.app = app
        self.db_path = db_path or "database/chatbot.db"
        
        # Simple department mapping
        self.departments = {
            "it_support": {"name": "IT Support", "email": "it@university.edu", "phone": "+1234567890"},
            "academic_affairs": {"name": "Academic Affairs", "email": "academic@university.edu", "phone": "+1234567891"},
            "finance": {"name": "Finance", "email": "finance@university.edu", "phone": "+1234567892"},
        }
        
        # Simple solutions
        self.access_solutions = {
            "login failed": "Please check your username and password. Use 'Forgot Password' if needed.",
            "password reset": "Click 'Forgot Password' on the login page to reset your password.",
            "account locked": "Contact IT Support to unlock your account.",
        }
        
        self.init_database()
        logger.info("Chatbot initialized")
    
    def init_database(self):
        try:
            import os
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_number TEXT,
                    student_id TEXT,
                    student_name TEXT,
                    student_email TEXT,
                    department TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Database error: {e}")
    
    def process_message(self, message, student_id=None, student_name=None, student_email=None, 
                       student_phone=None, session_id=None):
        # Simple response logic
        message_lower = message.lower()
        
        # Check if we have a solution
        for issue, solution in self.access_solutions.items():
            if issue in message_lower:
                return {
                    "success": True,
                    "response": solution,
                    "ticket_created": False
                }
        
        # Create a ticket if no solution
        if student_id and student_email:
            ticket_id = self.create_ticket(student_id, student_name, student_email, 
                                          student_phone, "it_support", message)
            return {
                "success": True,
                "response": f"Ticket created! ID: {ticket_id}. Support will contact you soon.",
                "ticket_created": True,
                "ticket_id": ticket_id
            }
        else:
            return {
                "success": True,
                "response": "Please provide your student ID and email to create a support ticket.",
                "need_student_info": True
            }
    
    def create_ticket(self, student_id, student_name, student_email, student_phone, department, description):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            ticket_number = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute('''
                INSERT INTO tickets (ticket_number, student_id, student_name, student_email, department, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ticket_number, student_id, student_name, student_email, department, description))
            ticket_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return ticket_id
        except Exception as e:
            logger.error(f"Ticket creation error: {e}")
            return -1
    
    def get_ticket_status(self, ticket_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tickets WHERE ticket_id = ?', (ticket_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"ticket_id": row[0], "status": row[6], "description": row[5]}
            return None
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    def get_tickets_by_student(self, student_id, limit=10):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT ticket_id, ticket_number, status, created_at FROM tickets WHERE student_id = ? LIMIT ?', 
                          (student_id, limit))
            rows = cursor.fetchall()
            conn.close()
            return [{"ticket_id": r[0], "ticket_number": r[1], "status": r[2], "created_at": r[3]} for r in rows]
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
    
    def get_department_stats(self):
        return {"total": 0, "open": 0, "resolved": 0}
    
    def update_ticket_status(self, ticket_id, status, resolution_notes=None, assigned_to=None):
        return True
    
    def add_feedback(self, ticket_id, student_id, rating, comment=None):
        return True
