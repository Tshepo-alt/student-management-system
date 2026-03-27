-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(50) NOT NULL DEFAULT 'student',
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Programs table
CREATE TABLE programs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    duration_years INTEGER DEFAULT 3
);

-- Courses table
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    program_id INTEGER NOT NULL REFERENCES programs(id),
    credits INTEGER DEFAULT 3,
    semester INTEGER
);

-- Students table
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    student_number VARCHAR(50) UNIQUE NOT NULL,
    program_id INTEGER NOT NULL REFERENCES programs(id),
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    gpa FLOAT DEFAULT 0.0
);

-- Alumni table
CREATE TABLE alumni (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    student_number VARCHAR(50) UNIQUE NOT NULL,
    graduation_date TIMESTAMP,
    current_job_title VARCHAR(150),
    company VARCHAR(150),
    employment_status VARCHAR(50),
    linkedin_url VARCHAR(255),
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assignments table
CREATE TABLE assignments (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    title VARCHAR(150) NOT NULL,
    description TEXT,
    due_date TIMESTAMP NOT NULL,
    max_score FLOAT DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assignment submissions table
CREATE TABLE assignment_submissions (
    id SERIAL PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES assignments(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    file_path VARCHAR(255) NOT NULL,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score FLOAT,
    feedback TEXT,
    status VARCHAR(50) DEFAULT 'submitted'
);

-- Exam registrations table
CREATE TABLE exam_registrations (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    exam_type VARCHAR(50) NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exam_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'registered',
    fee FLOAT NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'pending'
);

-- Accommodations table
CREATE TABLE accommodations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    address VARCHAR(255),
    capacity INTEGER,
    available_rooms INTEGER,
    price_per_semester FLOAT,
    amenities TEXT
);

-- Accommodation registrations table
CREATE TABLE accommodation_registrations (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL UNIQUE REFERENCES students(id),
    accommodation_id INTEGER NOT NULL REFERENCES accommodations(id),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    check_in_date TIMESTAMP,
    check_out_date TIMESTAMP,
    room_number VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    payment_status VARCHAR(50) DEFAULT 'pending'
);

-- Payments table
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    amount FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    payment_type VARCHAR(50),
    stripe_payment_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    payment_date TIMESTAMP,
    exam_registration_id INTEGER REFERENCES exam_registrations(id),
    accommodation_registration_id INTEGER REFERENCES accommodation_registrations(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_students_user_id ON students(user_id);
CREATE INDEX idx_students_program_id ON students(program_id);
CREATE INDEX idx_assignments_course_id ON assignments(course_id);
CREATE INDEX idx_submissions_student_id ON assignment_submissions(student_id);
CREATE INDEX idx_exam_registrations_student_id ON exam_registrations(student_id);
CREATE INDEX idx_accommodations_registrations_student_id ON accommodation_registrations(student_id);
CREATE INDEX idx_payments_student_id ON payments(student_id);
CREATE INDEX idx_payments_status ON payments(status);

-- Insert sample programs
INSERT INTO programs (name, code, description, duration_years) VALUES
('Computer Science', 'CS', 'Bachelor of Science in Computer Science', 4),
('Business Administration', 'BA', 'Bachelor of Business Administration', 3),
('Software Engineering', 'SE', 'Bachelor of Software Engineering', 4),
('Information Technology', 'IT', 'Bachelor of Information Technology', 3),
('Data Science', 'DS', 'Bachelor of Data Science', 3);

-- Insert sample courses
INSERT INTO courses (code, name, program_id, credits, semester) VALUES
('CS101', 'Introduction to Programming', 1, 3, 1),
('CS102', 'Data Structures', 1, 3, 2),
('CS201', 'Algorithms', 1, 3, 3),
('BA101', 'Business Fundamentals', 2, 3, 1),
('BA102', 'Marketing Basics', 2, 3, 1),
('SE101', 'Software Development Basics', 3, 3, 1),
('IT101', 'IT Fundamentals', 4, 3, 1),
('DS101', 'Data Analysis Basics', 5, 3, 1);

-- Insert sample accommodations
INSERT INTO accommodations (name, address, capacity, available_rooms, price_per_semester, amenities) VALUES
('North Campus Residence', '123 University Ave', 200, 45, 1500.00, 'WiFi, Laundry, Cafeteria, Security'),
('South Campus Dorms', '456 College St', 150, 30, 1200.00, 'WiFi, Study Rooms, Gym'),
('East Wing Apartments', '789 Student Blvd', 100, 15, 1800.00, 'WiFi, Furnished, Kitchen, Parking'),
('West Side Housing', '321 Park Lane', 120, 25, 1400.00, 'WiFi, Library Access, Recreation Center');