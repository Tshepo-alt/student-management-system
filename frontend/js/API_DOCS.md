# University Student Portal - API Documentation

Complete API reference for all endpoints.

## 📋 Base URL

```
http://localhost:5000/api
```

## 🔐 Authentication

Most endpoints require authentication via session (Flask-Login). Login first, then cookies are automatically included.

### Health Check

**GET** `/health`

No authentication required.

**Response:**
```json
{
  "status": "OK",
  "message": "Server is running",
  "environment": "development"
}
```

---

## 👤 Authentication Endpoints

### Register

**POST** `/auth/register`

Register a new student.

**Request Body:**
```json
{
  "email": "student@university.edu",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1 (555) 123-4567",
  "program_id": 1
}
```

**Response:**
```json
{
  "message": "Registration successful",
  "student_number": "STU123456",
  "email": "student@university.edu"
}
```

---

### Login

**POST** `/auth/login`

Authenticate user.

**Request Body:**
```json
{
  "email": "student@university.edu",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user_id": 1,
  "email": "student@university.edu",
  "role": "student"
}
```

---

### Logout

**POST** `/auth/logout`

Logout current user. Requires authentication.

**Response:**
```json
{
  "message": "Logout successful"
}
```

---

### Get Profile

**GET** `/auth/profile`

Get current user profile. Requires authentication.

**Response:**
```json
{
  "id": 1,
  "email": "student@university.edu",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1 (555) 123-4567",
  "role": "student",
  "email_verified": true,
  "student_number": "STU123456",
  "program_id": 1
}
```

---

### Update Profile

**PUT** `/auth/profile`

Update user profile. Requires authentication.

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "phone": "+1 (555) 987-6543"
}
```

**Response:**
```json
{
  "message": "Profile updated successfully"
}
```

---

### Change Password

**POST** `/auth/change-password`

Change user password. Requires authentication.

**Request Body:**
```json
{
  "old_password": "OldPass123",
  "new_password": "NewPass456"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

---

## 📚 Student Endpoints

### Dashboard

**GET** `/students/dashboard`

Get student dashboard information. Requires authentication.

**Response:**
```json
{
  "student_number": "STU123456",
  "program": "Computer Science",
  "status": "active",
  "gpa": 3.75,
  "enrollment_date": "2023-09-15T00:00:00",
  "pending_exams": 2,
  "accommodation_status": "approved",
  "user": {
    "name": "John Doe",
    "email": "student@university.edu"
  }
}
```

---

### Get Courses

**GET** `/students/courses`

Get enrolled courses. Requires authentication.

**Response:**
```json
[
  {
    "id": 1,
    "code": "CS101",
    "name": "Introduction to Programming",
    "credits": 3,
    "semester": 1
  },
  {
    "id": 2,
    "code": "CS102",
    "name": "Data Structures",
    "credits": 3,
    "semester": 2
  }
]
```

---

## 📝 Assignment Endpoints

### Get Assignments

**GET** `/assignments`

Get all assignments. Requires authentication.

**Response:**
```json
[
  {
    "id": 1,
    "title": "Assignment 1: Variables",
    "description": "Complete 10 programming exercises",
    "course_name": "Introduction to Programming",
    "due_date": "2026-04-15T23:59:59",
    "max_score": 100,
    "created_at": "2026-03-20T10:00:00"
  }
]
```

---

### Submit Assignment

**POST** `/assignments/{assignment_id}/submit`

Submit assignment file. Requires authentication.

**Request:** Multipart form data with file

**Response:**
```json
{
  "message": "Assignment submitted successfully"
}
```

---

### Get My Submissions

**GET** `/assignments/my-submissions`

Get all student submissions. Requires authentication.

**Response:**
```json
[
  {
    "id": 1,
    "assignment_title": "Assignment 1: Variables",
    "submission_date": "2026-04-10T14:30:00",
    "score": 95,
    "feedback": "Excellent work!",
    "status": "graded"
  }
]
```

---

## 📊 Exam Endpoints

### Get Supplementary Exams

**GET** `/exams/supplementary`

Get available supplementary exams. Requires authentication.

**Response:**
```json
[
  {
    "id": 1,
    "course_code": "CS101",
    "course_name": "Introduction to Programming",
    "credits": 3,
    "supplementary_fee": 50.0
  }
]
```

---

### Register Supplementary

**POST** `/exams/supplementary/register`

Register for supplementary exam. Requires authentication.

**Request Body:**
```json
{
  "course_id": 1
}
```

**Response:**
```json
{
  "message": "Supplementary exam registration successful",
  "registration_id": 1,
  "fee": 50.0,
  "payment_status": "pending"
}
```

---

### Get My Registrations

**GET** `/exams/my-registrations`

Get exam registrations. Requires authentication.

**Response:**
```json
[
  {
    "id": 1,
    "course_code": "CS101",
    "course_name": "Introduction to Programming",
    "exam_type": "supplementary",
    "fee": 50.0,
    "status": "registered",
    "payment_status": "pending",
    "registration_date": "2026-03-20T10:00:00",
    "exam_date": null
  }
]
```

---

## 💳 Payment Endpoints

### Create Payment Intent

**POST** `/payments/create-payment-intent`

Create Stripe payment intent. Requires authentication.

**Request Body:**
```json
{
  "amount": 50.0,
  "payment_type": "exam_fee",
  "currency": "usd",
  "exam_registration_id": 1
}
```

**Response:**
```json
{
  "clientSecret": "pi_xxxxx_secret_xxxxx",
  "paymentIntentId": "pi_xxxxx",
  "amount": 50.0,
  "currency": "usd"
}
```

---

### Confirm Payment

**POST** `/payments/confirm-payment`

Confirm payment after successful charge. Requires authentication.

**Request Body:**
```json
{
  "paymentIntentId": "pi_xxxxx"
}
```

**Response:**
```json
{
  "message": "Payment confirmed successfully",
  "paymentId": 1,
  "amount": 50.0,
  "status": "completed"
}
```

---

### Get Payment History

**GET** `/payments/history?page=1&per_page=10`

Get payment history. Requires authentication.

**Response:**
```json
{
  "payments": [
    {
      "id": 1,
      "amount": 50.0,
      "currency": "USD",
      "payment_type": "exam_fee",
      "status": "completed",
      "payment_date": "2026-03-20T14:30:00",
      "created_at": "2026-03-20T10:00:00"
    }
  ],
  "total": 5,
  "pages": 1,
  "current_page": 1
}
```

---

## 🏠 Accommodation Endpoints

### Get Available Accommodation

**GET** `/accommodation/available`

Get available accommodation options. Requires authentication.

**Response:**
```json
[
  {
    "id": 1,
    "name": "North Campus Residence",
    "address": "123 University Ave",
    "capacity": 200,
    "available_rooms": 45,
    "price_per_semester": 1500.0,
    "amenities": "WiFi, Laundry, Cafeteria, Security"
  }
]
```

---

### Register Accommodation

**POST** `/accommodation/register`

Register for accommodation. Requires authentication.

**Request Body:**
```json
{
  "accommodation_id": 1
}
```

**Response:**
```json
{
  "message": "Accommodation registration successful",
  "registration_id": 1,
  "price_per_semester": 1500.0,
  "status": "pending",
  "payment_status": "pending"
}
```

---

### Get My Accommodation

**GET** `/accommodation/my-accommodation`

Get current accommodation registration. Requires authentication.

**Response:**
```json
{
  "registration_id": 1,
  "accommodation_name": "North Campus Residence",
  "address": "123 University Ave",
  "room_number": "A-215",
  "check_in_date": "2026-09-01T00:00:00",
  "check_out_date": "2026-05-30T00:00:00",
  "status": "approved",
  "payment_status": "paid",
  "price_per_semester": 1500.0,
  "amenities": "WiFi, Laundry, Cafeteria, Security",
  "registration_date": "2026-03-20T10:00:00"
}
```

---

## 👥 Alumni Endpoints

### Get Alumni Profile

**GET** `/alumni/profile`

Get current user's alumni profile. Requires authentication.

**Response:**
```json
{
  "id": 1,
  "student_number": "STU123456",
  "name": "John Doe",
  "email": "john@example.com",
  "graduation_date": "2025-05-30T00:00:00",
  "current_job_title": "Software Engineer",
  "company": "Tech Company Inc",
  "employment_status": "employed",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "bio": "Software engineer with 2 years of experience..."
}
```

---

### Update Alumni Profile

**PUT** `/alumni/profile`

Update alumni profile. Requires authentication.

**Request Body:**
```json
{
  "current_job_title": "Senior Software Engineer",
  "company": "Big Tech Corp",
  "employment_status": "employed",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "bio": "Senior software engineer with 3 years of experience..."
}
```

**Response:**
```json
{
  "message": "Alumni profile updated successfully"
}
```

---

### Get Alumni Directory

**GET** `/alumni/directory?page=1&per_page=20`

Get alumni directory. No authentication required.

**Response:**
```json
{
  "alumni": [
    {
      "id": 1,
      "name": "John Doe",
      "company": "Tech Company Inc",
      "job_title": "Software Engineer",
      "employment_status": "employed",
      "linkedin_url": "https://linkedin.com/in/johndoe",
      "graduation_date": "2025-05-30"
    }
  ],
  "total": 150,
  "pages": 8,
  "current_page": 1
}
```

---

### Get Employment Statistics

**GET** `/alumni/employment-stats`

Get employment statistics. No authentication required.

**Response:**
```json
{
  "total_alumni": 500,
  "employed": 425,
  "unemployed": 50,
  "self_employed": 25,
  "employment_rate": 85.0
}
```

---

### Search Alumni

**GET** `/alumni/search?q=John`

Search alumni by name or company. No authentication required.

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "company": "Tech Company Inc",
    "job_title": "Software Engineer",
    "employment_status": "employed"
  }
]
```

---

## ❌ Error Responses

### 400 - Bad Request
```json
{
  "error": "Missing required fields"
}
```

### 401 - Unauthorized
```json
{
  "error": "Please log in to access this page"
}
```

### 403 - Forbidden
```json
{
  "error": "Unauthorized"
}
```

### 404 - Not Found
```json
{
  "error": "Resource not found"
}
```

### 500 - Server Error
```json
{
  "error": "Internal server error"
}
```

---

## 🧪 Testing with cURL

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@uni.edu","password":"Pass123","first_name":"Test","last_name":"User","phone":"1234567890","program_id":1}' \
  -c cookies.txt

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@uni.edu","password":"Pass123"}' \
  -c cookies.txt

# Get Dashboard
curl -X GET http://localhost:5000/api/students/dashboard \
  -b cookies.txt
```

---

**API Version**: 1.0.0
**Last Updated**: March 2026