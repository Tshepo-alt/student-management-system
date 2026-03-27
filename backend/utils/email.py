from flask import render_template_string
from flask_mail import Mail, Message
import os

mail = Mail()

class EmailService:
    """Handle email notifications"""
    
    @staticmethod
    def send_registration_confirmation(user_email, first_name, student_number):
        """Send registration confirmation email"""
        try:
            subject = "Welcome to University Student Portal - Registration Confirmation"
            
            body = f"""
            <html>
                <body>
                    <h2>Welcome to University Student Portal!</h2>
                    <p>Dear {first_name},</p>
                    <p>Your registration has been successful.</p>
                    <p><strong>Your Student Number:</strong> {student_number}</p>
                    <p>You can now log in to the portal using your email and password.</p>
                    <p>Best regards,<br>University Administration</p>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_assignment_submission_confirmation(user_email, first_name, assignment_title):
        """Send assignment submission confirmation"""
        try:
            subject = f"Assignment Submitted - {assignment_title}"
            
            body = f"""
            <html>
                <body>
                    <h2>Assignment Submission Confirmation</h2>
                    <p>Dear {first_name},</p>
                    <p>Your assignment <strong>{assignment_title}</strong> has been submitted successfully.</p>
                    <p>You will receive feedback from your instructor shortly.</p>
                    <p>Best regards,<br>University Administration</p>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_exam_registration_confirmation(user_email, first_name, course_name, exam_type, fee):
        """Send exam registration confirmation"""
        try:
            subject = f"{exam_type.title()} Exam Registration - {course_name}"
            
            body = f"""
            <html>
                <body>
                    <h2>Exam Registration Confirmation</h2>
                    <p>Dear {first_name},</p>
                    <p>You have successfully registered for a {exam_type} exam.</p>
                    <p><strong>Course:</strong> {course_name}</p>
                    <p><strong>Fee:</strong> ${fee}</p>
                    <p>Please proceed to make payment through the portal.</p>
                    <p>Best regards,<br>University Administration</p>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_payment_confirmation(user_email, first_name, amount, payment_type):
        """Send payment confirmation"""
        try:
            subject = f"Payment Confirmation - {amount} {payment_type.replace('_', ' ').title()}"
            
            body = f"""
            <html>
                <body>
                    <h2>Payment Confirmation</h2>
                    <p>Dear {first_name},</p>
                    <p>Your payment has been processed successfully.</p>
                    <p><strong>Amount:</strong> ${amount}</p>
                    <p><strong>Payment Type:</strong> {payment_type.replace('_', ' ').title()}</p>
                    <p>Thank you for your payment.</p>
                    <p>Best regards,<br>University Administration</p>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_accommodation_confirmation(user_email, first_name, accommodation_name, price):
        """Send accommodation registration confirmation"""
        try:
            subject = f"Accommodation Registration - {accommodation_name}"
            
            body = f"""
            <html>
                <body>
                    <h2>Accommodation Registration Confirmation</h2>
                    <p>Dear {first_name},</p>
                    <p>Your accommodation request has been received.</p>
                    <p><strong>Accommodation:</strong> {accommodation_name}</p>
                    <p><strong>Price per Semester:</strong> ${price}</p>
                    <p>Your request is pending approval. You will receive an update soon.</p>
                    <p>Best regards,<br>University Administration</p>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False