# TANGAMAKURU - Rwanda Crime Reporting System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12%2B-blue.svg)](https://www.postgresql.org/)

A comprehensive digital platform for reporting and managing crime incidents in Rwanda. Citizens can report incidents with evidence, officers can manage cases, and administrators can oversee the entire system.

## 📋 Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Project Structure](#project-structure)
- [Default Accounts](#default-accounts)
- [Usage Guide](#usage-guide)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)

## ✨ Features

### 👥 Citizen Portal
- Submit incident reports with evidence (images and documents)
- Track report status in real-time (Pending → In Progress → Resolved)
- Receive notifications about case updates
- Respond to officer requests for additional information
- View all submitted reports with filters

### 👮 Officer Dashboard
- View and manage assigned incidents
- Update case status with detailed comments
- Request additional information from citizens
- Communicate with admin via built-in messaging system
- Generate monthly statistical reports with PDF export
- View incident details with all evidence

### 🛡️ Admin Dashboard
- Manage officers in their district
- Approve or deny new officer registrations
- View all reports in the district with sector filtering
- Assign unassigned reports to officers
- Send announcements to officers in specific sectors
- Communicate with officers via messaging system
- View real-time statistics and charts

### 👑 Super Admin
- Create and manage district administrators
- System-wide maintenance announcements
- Admin account management (activate/deactivate/delete)
- View system-wide statistics

## 🛠 Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask 2.3.3 (Python 3.10+) |
| Database | PostgreSQL 12+ |
| ORM | SQLAlchemy 2.0 |
| Migrations | Flask-Migrate / Alembic |
| Frontend | Bootstrap 5, JavaScript, Jinja2 |
| Authentication | Session-based with Flask-Login |
| PDF Generation | WeasyPrint |
| File Uploads | Local storage with secure filenames |
| Charts | Matplotlib |
| Background Tasks | Celery with Redis |
| Email | Flask-Mail (optional) |

## 📋 Prerequisites

- **Python 3.10 or 3.11** (Python 3.12 has compatibility issues with datetime functions)
- **PostgreSQL 12 or higher**
- **Git** (for cloning the repository)
- **Redis** (optional, for Celery background tasks)

## 🚀 Installation Steps

---

## 1️Clone the Repository

```bash
git clone https://github.com/attorney755/Tangamakuru.git
cd Tangamakuru
```

---

## 2️Create and Activate Virtual Environment

- **Linux/macOS:**
  ```bash
  python3.10 -m venv venv
  source venv/bin/activate
  ```
- **Windows:**
  ```cmd
  python -m venv venv
  venv\Scripts\activate
  ```

---

## 3️Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

You're absolutely right! Let's improve the README to include PostgreSQL installation instructions for all platforms. Here's the updated section:

---

## 4️ Set Up PostgreSQL Database

### 📦 Install PostgreSQL (if not already installed)

**Check if PostgreSQL is installed:**
```bash
# Check PostgreSQL version
psql --version
# Or for Linux
which psql
```

If PostgreSQL is not installed, follow the instructions for your operating system:

#### 🐧 **Linux (Ubuntu/Debian)**
```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 🍎 **macOS**
```bash
# Using Homebrew
brew install postgresql

# Start PostgreSQL service
brew services start postgresql
```

#### 🪟 **Windows**
1. Download the installer from [postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
2. Run the installer and follow the setup wizard
3. Note the password you set for the `postgres` user
4. Add PostgreSQL to your system PATH (usually `C:\Program Files\PostgreSQL\15\bin`)

### 🔧 Start PostgreSQL Service

**Linux:**
```bash
sudo systemctl start postgresql
```

**macOS:**
```bash
brew services start postgresql
```

**Windows:** PostgreSQL starts automatically as a Windows service after installation.

### 🗄️ Create Database and User

Login to PostgreSQL and create the database:

```bash
# Login to PostgreSQL
sudo -u postgres psql
```

**For Windows:** Open Command Prompt as Administrator and run:
```bash
psql -U postgres
```
(Enter the password you set during installation)

Run these SQL commands:
```sql
CREATE DATABASE tangamakuru_db;
CREATE USER tangamakuru_user WITH PASSWORD 'your_secure_password';
ALTER ROLE tangamakuru_user SET client_encoding TO 'utf8';
ALTER ROLE tangamakuru_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tangamakuru_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tangamakuru_db TO tangamakuru_user;
\q
```

---

## 5️ Configure Environment Variables

Create a `.env` file in the `backend` directory:
```bash
cd backend
cp .env.example .env
nano .env  # or use any text editor (vim, code, etc.)
```

`.env` file content:
```ini
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-this-in-production
FLASK_APP=run.py
FLASK_ENV=development

# Database Configuration
DATABASE_URL=postgresql://tangamakuru_user:your_secure_password@localhost/tangamakuru_db

# Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB

# Email Configuration (optional - use for email notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

---

## 6️Create Database Tables (Run Migrations)

Important: The database is empty after creation. You need to create all the tables (users, reports, media, messages, etc.) using Flask-Migrate.

```bash
cd backend
```

```bash
# Run database migrations to create all tables
flask db upgrade
```

If you see an error like "No such command 'db'", make sure you're in the virtual environment:
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

---

## 7️ Create Uploads Directory

Create the uploads folder in the `backend` directory to store evidence files:

```bash
cd backend
mkdir -p uploads
chmod 755 uploads  # Optional: set permissions
```

---

## 🗃️ **Database Schema Overview**

When you run `flask db upgrade`, the following tables will be **automatically created**:

| **Table Name**          | **Description**                                                                 |
|-------------------------|-------------------------------------------------------------------------------|
| **`users`**             | Stores all user accounts (citizens, officers, admins, and super admin).       |
| **`reports`**           | Stores all incident reports submitted by citizens.                           |
| **`media`**             | Stores evidence files (images, videos, documents) attached to reports.       |
| **`messages`**          | Stores conversations between admins and officers.                           |
| **`notifications`**     | Stores system notifications for users (e.g., report updates, requests).     |
| **`announcements`**     | Stores system-wide announcements created by admins.                          |
| **`pending_approvals`** | Tracks officer registration requests awaiting approval by district admins.  |
| **`user_announcements`**| Stores personalized copies of announcements for individual users.            |

---

## 🔧 Troubleshooting Database Issues

### ❌ "psql: command not found"
- PostgreSQL is not installed or not in PATH. Reinstall or add PostgreSQL bin directory to PATH.

### ❌ "FATAL: password authentication failed for user 'postgres'"
- Reset PostgreSQL password:
  ```bash
  sudo -u postgres psql
  ALTER USER postgres WITH PASSWORD 'new_password';
  \q
  ```

### ❌ "ERROR: database 'tangamakuru_db' already exists"
- Drop the existing database first:
  ```sql
  DROP DATABASE IF EXISTS tangamakuru_db;
  CREATE DATABASE tangamakuru_db;
  ```

### ❌ "flask: command not found"
- Activate virtual environment first:
  ```bash
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```

### ❌ "No such command 'db'"
- Flask-Migrate is not installed. Install it:
  ```bash
  pip install Flask-Migrate
  ```

---
```

---

## 8️ Create the Super Admin Account

After setting up the database and running migrations, create the Super Admin account using the interactive script:

### Step 1: Run the Super Admin Creation Script

```bash
cd backend
python create_super_admin.py
```

You will see the following prompt:

---

## 🔐 **Super Admin Account Setup**

```plaintext
==================================================
TANGAMAKURU - Super Admin Account Setup
==================================================

This account will have full system access.
It can create district administrators who will manage officers.

Enter Super Admin email address:
(Note: Must end with @gov.rw, e.g., superadmin@gov.rw)

First Name: [Enter your first name]
Last Name: [Enter your last name]

Create a strong password (minimum 8 characters): [Enter your password]
```

### **Notes:**
- The **email address** must end with `@gov.rw` (e.g., `superadmin@gov.rw`).
- The **password** must be at least **8 characters** long.
- This account will have **full administrative privileges** to manage the entire platform.

---

## 9️ Start the Application

```bash
python run.py
```
The application will be available at: [http://localhost:5000](http://localhost:5000)

---

## 🌐 **Testing the Platform Online**

You can test the **Tangamakuru** platform online using the following **Super Admin** credentials:

### **Login Details**
| **Email**            | **Password**      |
|----------------------|--------------------|
| `superadmin@gov.rw`  | `Vanessa@2025`     |

### **Access the Platform**
🔗 **[Visit Tangamakuru Online](https://tangamakuru.onrender.com)**

---
**Note:** These credentials are for **testing purposes only**. Use them to explore the platform’s features, including:
- Super Admin dashboard
- Officer and citizen workflows
- Reporting and case management

---

## 📁 Project Structure

```
Tangamakuru/
├── backend/
│   ├── app/
│   │   ├── routes/           # All route handlers
│   │   │   ├── admin.py      # Admin dashboard routes
│   │   │   ├── frontend.py   # Public pages and citizen routes
│   │   │   ├── officer.py    # Officer dashboard routes
│   │   │   ├── reports.py    # Report submission and viewing
│   │   │   └── super_admin.py # Super admin routes
│   │   ├── utils/            # Utility functions
│   │   │   ├── notifications.py # Notification system
│   │   │   ├── report_generator.py # PDF report generation
│   │   │   └── email.py      # Email sending
│   │   ├── __init__.py       # Flask app factory
│   │   ├── auth.py           # Authentication logic
│   │   ├── models.py         # Database models
│   │   ├── middleware.py     # Session timeout middleware
│   │   └── template_filters.py # Custom Jinja2 filters
│   ├── migrations/           # Database migrations
│   ├── uploads/              # Uploaded files (created on first upload)
│   ├── requirements.txt      # Python dependencies
│   ├── run.py               # Application entry point
│   ├── create_admin.py      # Create default users
│   └── .env.example         # Environment variables template
├── frontend/
│   └── templates/           # All HTML templates
│       ├── admin/           # Admin dashboard templates
│       ├── officer/         # Officer dashboard templates
│       ├── super_admin/     # Super admin templates
│       ├── base.html        # Base template with navbar
│       ├── landing.html     # Landing page
│       ├── login.html       # Login page
│       ├── register.html    # Citizen registration
│       ├── officer_register.html  # Officer registration
│       ├── notifications.html     # Notification center
│       └── view_report.html       # Report details page
└── README.md                # This file
```

---

## 🔑 Default Accounts

After running `create_admin.py`, these accounts are created:

| Role         | Email                  | Password       |
|--------------|------------------------|----------------|
| Super Admin  | superadmin@gov.rw      | Vanessa@2025   |


**Note:** This account is for testing purposes only and district admins must be created by the Super Admin from the dashboard.

---

## 📖 Usage Guide

### For Citizens
- **Register:** Click "Register" on the landing page, select "As Citizen"
- **Submit Report:** After login, click "Submit Report" and fill in incident details
- **Upload Evidence:** Add images, videos, or documents as evidence
- **Track Report:** View all your reports in the dashboard
- **Respond to Requests:** If an officer requests more information, you'll see a notification with a response form

### For Officers
- **Registration:** Go to `/officer/register` or click "Register as Officer"
- **Wait for Approval:** Your district admin must approve your account
- **Login:** After approval, log in to access your dashboard
- **View Incidents:** See all assigned incidents in your sector
- **Update Status:** Change case status (Pending → In Progress → Resolved) with comments
- **Request Information:** Click "Request Information" to ask citizens for more details
- **Messages:** Check messages from admin about specific cases
- **Generate Reports:** Create monthly PDF reports with statistics

### For Admins
- **Login:** Use your admin credentials (provided by super admin)
- **Approve Officers:** Click "New Officers" in the dropdown to approve pending registrations
- **Manage Officers:** View all officers in your district, activate/deactivate as needed
- **View Reports:** See all reports in your district, filter by sector
- **Assign Reports:** Assign unassigned reports to officers in your district
- **Messages:** Communicate with officers about specific cases
- **Announcements:** Create announcements for officers (can target specific sectors)

### For Super Admin
- **Login:** Use super admin credentials
- **Manage Admins:** Create new district admins, edit or delete existing ones
- **System Announcements:** Create maintenance announcements for all users
- **View Statistics:** See system-wide stats (total admins, officers, citizens)

---

## 🛠 Troubleshooting

### Python 3.12 datetime error
**Error:**
```
AttributeError: module 'datetime' has no attribute 'utcnow'
```
**Solution:** Use Python 3.10 or 3.11. The app is tested with Python 3.10.

### Database connection error
**Error:**
```
psycopg2.OperationalError: could not connect to server
```
**Solution:** Ensure PostgreSQL is running:
```bash
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS
```

### Upload folder permission error
**Error:**
```
PermissionError: [Errno 13] Permission denied: 'uploads'
```
**Solution:**
```bash
mkdir -p uploads
chmod 755 uploads
```

### Migration error - missing tables
**Error:**
```
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```
**Solution:**
```bash
flask db upgrade
```

### Missing secret key error
**Error:**
```
RuntimeError: The session is unavailable because no secret key was set
```
**Solution:** Make sure `.env` file exists and contains `SECRET_KEY=your-secret-key`

---

## 🔒 Security Notes
- Never commit the `.env` file to version control
- Change default passwords in production
- Use HTTPS in production (configure with Nginx/Apache)
- Set `FLASK_ENV=production` in production
- Regularly update dependencies: `pip install --upgrade -r requirements.txt`
- Set `SESSION_COOKIE_SECURE = True` when using HTTPS

---

## 📄 License
Copyright © 2026 Attorney Valois NIYIGABA. All rights reserved.

---

## 👨‍💻 Author
**Attorney Valois NIYIGABA**
- GitHub: [attorney755](https://github.com/attorney755)
- Email: [attorneyvalois@gmail.com](mailto:attorneyvalois@gmail.com)

---

## 🙏 Acknowledgments
- Rwanda National Police for the inspiration
- Flask community for the excellent framework
- Bootstrap for the responsive design components
