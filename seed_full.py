# seed_full.py
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config import config
from models import db, Campus, Program, Module, ProgramModule, Student, User, AcademicYear, Semester, Registration, Enrollment
from datetime import date, datetime

app = Flask(__name__)
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])
db.init_app(app)

def main():
    with app.app_context():
        # 1. Campus
        campus = Campus.query.filter_by(campus_code="GAB").first()
        if not campus:
            campus = Campus(
                campus_code="GAB",
                campus_name="Gaborone Main Campus",
                campus_location="Gaborone, Botswana",
                has_accommodation=True,
                is_main_campus=True
            )
            db.session.add(campus)
            db.session.flush()
            print("✅ Created Gaborone Main Campus.")
        else:
            print(f"✅ Campus already exists: {campus.campus_name}")

        # 2. Program
        program = Program.query.filter_by(program_code="BSC-CS").first()
        if not program:
            program = Program(
                program_code="BSC-CS",
                program_name="Bachelor of Science in Computer Science",
                campus_id=campus.id,
                duration_years=4,
                total_credits=480,
                min_bgcse_points=32,
                is_active=True
            )
            db.session.add(program)
            db.session.flush()
            print("✅ Created Bachelor of Science in Computer Science program.")
        else:
            print(f"✅ Program already exists: {program.program_name}")

        # 3. Modules
        modules_data = [
            ("CS101", "Introduction to Programming", 12, 1, 1),
            ("CS102", "Computer Architecture", 12, 1, 1),
            ("MA101", "Mathematics for Computing", 12, 1, 1),
        ]
        for code, name, credits, year, sem in modules_data:
            m = Module.query.filter_by(module_code=code).first()
            if not m:
                m = Module(
                    module_code=code,
                    module_name=name,
                    credits=credits,
                    year_level=year,
                    semester=sem,
                    is_active=True
                )
                db.session.add(m)
                db.session.flush()
                print(f"   Module created: {code}")
            # Link to program if not already linked
            if not ProgramModule.query.filter_by(program_id=program.id, module_id=m.id).first():
                pm = ProgramModule(program_id=program.id, module_id=m.id, is_compulsory=True)
                db.session.add(pm)
                print(f"   Linked {code} to program.")
        db.session.commit()
        print("✅ Modules and program-module links ready.")

        # 4. Get student user
        student_user = User.query.filter_by(email="student@example.com").first()
        if not student_user:
            print("❌ Student user not found. Run create_demo_users.py first.")
            return
        student = Student.query.filter_by(user_id=student_user.id).first()
        if not student:
            print("❌ Student record not found.")
            return

        # Update student program and campus
        if not student.program_id:
            student.program_id = program.id
        if not student.campus_id:
            student.campus_id = campus.id
        student.current_year = 1
        db.session.commit()
        print(f"✅ Updated student {student.email} (id={student.id}) with program and campus.")

        # 5. Academic year and semester
        academic_year = AcademicYear.query.filter_by(is_current=True).first()
        if not academic_year:
            academic_year = AcademicYear(
                year_name="2025/2026",
                start_date=date(2025, 7, 1),
                end_date=date(2026, 6, 30),
                is_current=True
            )
            db.session.add(academic_year)
            db.session.flush()
            print("✅ Created academic year 2025/2026.")

        semester = Semester.query.filter_by(academic_year_id=academic_year.id, semester_number=1).first()
        if not semester:
            semester = Semester(
                academic_year_id=academic_year.id,
                semester_number=1,
                semester_name="Semester 1",
                start_date=date(2025, 7, 15),
                end_date=date(2025, 12, 15),
                is_active=True
            )
            db.session.add(semester)
            db.session.flush()
            print("✅ Created Semester 1.")

        # 6. Registration (approved)
        registration = Registration.query.filter_by(student_id=student.id, academic_year_id=academic_year.id, semester_id=semester.id).first()
        if not registration:
            registration = Registration(
                student_id=student.id,
                academic_year_id=academic_year.id,
                semester_id=semester.id,
                year_of_study=1,
                registration_date=date.today(),
                sponsorship_type='private',
                registration_status='approved',
                payment_status='completed',
                total_fees=0,
                paid_amount=0
            )
            db.session.add(registration)
            db.session.flush()
            print("✅ Created approved registration.")
        else:
            print("Registration already exists.")

        # 7. Enrollments for each module
        for module in [Module.query.filter_by(module_code=code).first() for code in ["CS101","CS102","MA101"]]:
            if module:
                existing = Enrollment.query.filter_by(registration_id=registration.id, module_id=module.id).first()
                if not existing:
                    enrollment = Enrollment(
                        registration_id=registration.id,
                        student_id=student.id,
                        module_id=module.id,
                        enrollment_date=date.today(),
                        status='registered'
                    )
                    db.session.add(enrollment)
                    print(f"   Enrolled in {module.module_code}")
        db.session.commit()
        print("✅ Enrollments created.")

        print("\n🎉 Seeding complete. student@example.com can now see courses in the dashboard.")

if __name__ == '__main__':
    main()