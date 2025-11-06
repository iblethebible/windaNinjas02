# Customer Management System

A Flask web application for managing customer information with a modern, user-friendly interface.

## Features

- **Dashboard**: Overview of customer statistics and recent additions
- **Customer Management**: Full CRUD operations (Create, Read, Update, Delete)
- **Modern UI**: Beautiful, responsive design with Bootstrap 5
- **Database Integration**: Connects to MySQL/MariaDB backend

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database Connection

Create a `.env` file in the root directory with your database credentials:

```env
DATABASE_URL=mysql+pymysql://username:password@localhost/dbname
SECRET_KEY=your-secret-key-here
```

Or set environment variables directly:

```bash
# Windows PowerShell
$env:DATABASE_URL="mysql+pymysql://username:password@localhost/dbname"
$env:SECRET_KEY="your-secret-key-here"

# Linux/Mac
export DATABASE_URL="mysql+pymysql://username:password@localhost/dbname"
export SECRET_KEY="your-secret-key-here"
```

### 3. Database Schema

The application expects a `customer` table with the following structure:

```sql
CREATE TABLE customer (
    idcustomer INT AUTO_INCREMENT PRIMARY KEY,
    org_id INT,
    address_id INT,
    customer_to_job_id INT,
    forename VARCHAR(45),
    surname VARCHAR(45),
    timestamp DATETIME,
    email VARCHAR(45),
    telephone INT
);
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Routes

- `/` - Dashboard (home page)
- `/customers` - List all customers
- `/customers/add` - Add a new customer
- `/customers/<id>/edit` - Edit a customer
- `/customers/<id>/delete` - Delete a customer (POST)
- `/api/customers` - JSON API endpoint for all customers

## Project Structure

```
WNv2/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── templates/            # HTML templates
    ├── base.html         # Base template
    ├── dashboard.html    # Dashboard page
    ├── customers.html    # Customer list page
    ├── add_customer.html # Add customer form
    └── edit_customer.html # Edit customer form
```

## Notes

- The application uses SQLAlchemy ORM for database operations
- All customer fields except `idcustomer` are optional
- The `timestamp` field is automatically set when creating new customers
- The application includes flash messages for user feedback
- Search functionality is available on the customers list page

