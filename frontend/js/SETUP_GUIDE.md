# University Student Management System - Setup Guide

Complete step-by-step guide to set up and run the project.

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Git
- VS Code (recommended)
- Node.js (optional, for future enhancements)

## 🚀 Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/Tshepo-alt/student-management-system.git
cd student-management-system
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Set Up PostgreSQL Database

#### On Windows:
```bash
# Open Command Prompt and login to PostgreSQL
psql -U postgres

# Create database (inside psql)
CREATE DATABASE student_portal;
\q

# Load schema
psql -U postgres -d student_portal -f database/schema.sql
```

#### On macOS/Linux:
```bash
# Create database
createdb student_portal

# Load schema
psql student_portal < database/schema.sql
```

### Step 5: Configure Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit .env with your settings
# Update these values:
# - DATABASE_URL: postgresql://postgres:YOUR_PASSWORD@localhost:5432/student_portal
# - SECRET_KEY: Generate a random key (at least 32 characters)
# - STRIPE keys (can be added later for payments)
```

### Step 6: Run the Backend Server

```bash
# Make sure virtual environment is activated
python backend/app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

### Step 7: Test the API

Open a new terminal and test:

```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{"status": "OK", "message": "Server is running", "environment": "development"}
```

### Step 8: Open Frontend

- Open `frontend/index.html` in your browser or use a local server:

```bash
# Using Python's built-in server
cd frontend
python -m http.server 8000
```

Visit: `http://localhost:8000`

## 📁 Project Structure

```
student-management-system/
├── backend/
│   ├── __init__.py
│   ├── app.py                 # Main Flask app
│   ├── config.py              # Configuration
│   ├── models.py              # Database models
│   ├── routes/                # API routes
│   │   ├── auth.py            # Authentication
│   │   ├── students.py        # Student management
│   │   ├── alumni.py          # Alumni management
│   │   ├── assignments.py     # Assignments
│   │   ├── exams.py           # Exam registration
│   │   ├── payments.py        # Payment processing
│   │   └── accommodation.py   # Accommodation
│   └── utils/
│       ├── email.py           # Email service
│       └── stripe_handler.py  # Stripe utilities
├── frontend/
│   ├── index.html             # Home page
│   ├── pages/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── student-dashboard.html
│   │   ├── assignments.html
│   │   ├── exam-registration.html
│   │   ├── accommodation.html
│   │   └── alumni-portal.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js             # API calls
│       ├── payment.js         # Stripe integration
│       └── main.js            # Common functions
├── database/
│   └── schema.sql             # Database schema
├── .env.example               # Environment template
├── .env                       # Your local config (don't commit)
├── .gitignore
├── requirements.txt           # Python dependencies
├── README.md
└─�� SETUP_GUIDE.md            # This file
```

## 🔐 Database Setup Details

### Sample Data

The schema automatically inserts:
- **5 Programs**: Computer Science, Business, Software Engineering, IT, Data Science
- **8 Sample Courses**: Spread across different programs
- **4 Accommodations**: Different on-campus housing options

### Create Admin User (Optional)

```python
# Run this in Python shell after backend starts
from backend.app import create_app, db
from backend.models import User, Student, Program
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # Create admin user
    admin = User(
        email='admin@university.edu',
        password_hash=generate_password_hash('Admin@123'),
        first_name='Admin',
        last_name='User',
        role='admin',
        email_verified=True
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin user created!")
```

## 💳 Stripe Setup (For Payments)

1. Go to https://stripe.com
2. Create a free account
3. Get your API keys from Dashboard → Developers → API Keys
4. Update `.env`:
   ```
   STRIPE_PUBLIC_KEY=pk_test_YOUR_KEY
   STRIPE_SECRET_KEY=sk_test_YOUR_KEY
   ```
5. Test payments with Stripe test card: `4242 4242 4242 4242`

## 📧 Email Configuration (Optional)

### Using Gmail:

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to myaccount.google.com/security
   - Find "App passwords"
   - Select Mail and Windows Computer
   - Copy the generated password
3. Update `.env`:
   ```
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=generated-app-password
   ```

## 🧪 Testing

### Test Student Registration

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.com",
    "password": "Password123",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "program_id": 1
  }'
```

### Test Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.com",
    "password": "Password123"
  }'
```

## 🐛 Troubleshooting

### Issue: "psycopg2 module not found"
```bash
pip install psycopg2-binary
```

### Issue: "Database connection refused"
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Run: `psql -U postgres` to test connection

### Issue: "Port 5000 already in use"
```bash
# Change port in app.py
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Issue: "CORS errors in frontend"
- Backend CORS is already configured
- Make sure backend is running on localhost:5000
- Update `API_BASE_URL` in `frontend/js/api.js` if needed

## 📚 API Documentation

See [API_DOCS.md](API_DOCS.md) for complete API endpoint documentation.

## 🚢 Deployment

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md)

## 📝 Common Commands

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run backend
python backend/app.py

# Database backup
pg_dump student_portal > backup.sql

# Database restore
psql student_portal < backup.sql

# Run tests
pytest
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Create a pull request

## 📞 Support

For issues or questions:
- Check existing issues on GitHub
- Create a new issue with details
- Contact: support@university.edu

## 📄 License

MIT License - See LICENSE file

---

**Last Updated**: March 2026
**Version**: 1.0.0