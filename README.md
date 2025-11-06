# Winda Ninjas - Job Management System

A comprehensive Flask web application for managing window cleaning jobs, customers, zones, and worker tracking with a modern dark-themed interface.

## Features

### Core Functionality
- **Dashboard**: Overview of due jobs, unpaid earnings, and jobs by due date with zone filtering
- **Customer Management**: Full CRUD operations with optional surname support
- **Job Management**: Complete job lifecycle management with addresses, zones, and frequencies
- **Zone Management**: Organize jobs by geographic zones with admin controls
- **Payment Tracking**: Track completed jobs and mark payments received
- **Statistics & Analytics**: 
  - Zone-based revenue and job count charts
  - Zone distribution pie chart
  - Weekly earnings comparison (theoretical vs actual)
- **Due Jobs Tracking**: View and filter jobs by due date and zone
- **Unpaid Jobs**: Track and manage unpaid completed jobs
- **Admin Settings**: Manage zones and system configuration

### User Interface
- **Dark Mode**: Modern dark theme with red accent colors
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Bootstrap 5**: Modern UI components and styling
- **Chart.js Integration**: Interactive charts and graphs for statistics

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- MySQL or MariaDB database
- pip (Python package manager)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Database Connection

Create a `.env` file in the root directory:

```env
DATABASE_URL=mysql+pymysql://username:password@localhost/dbname
SECRET_KEY=your-secret-key-here-change-in-production
```

**Generate a secure SECRET_KEY:**
```python
import secrets
print(secrets.token_hex(32))
```

### 4. Database Schema

The application requires the following tables:

```sql
-- Customer table
CREATE TABLE customer (
    idcustomer INT AUTO_INCREMENT PRIMARY KEY,
    org_id INT,
    address_id INT,
    forename VARCHAR(45),
    surname VARCHAR(45),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(45),
    telephone INT
);

-- Address table
CREATE TABLE address (
    idaddress INT AUTO_INCREMENT PRIMARY KEY,
    house_num_name VARCHAR(100),
    street_name VARCHAR(100),
    postcode VARCHAR(100),
    latitude VARCHAR(100),
    longitude VARCHAR(100)
);

-- Zone table
CREATE TABLE zone (
    idzone INT AUTO_INCREMENT PRIMARY KEY,
    org_id INT,
    name VARCHAR(100) NOT NULL
);

-- Jobs table
CREATE TABLE jobs (
    idjob INT AUTO_INCREMENT PRIMARY KEY,
    price DECIMAL(10,2),
    dateLastDone DATE,
    frequency INT,
    org_id INT,
    address_id INT,
    zone_id INT,
    customer_id INT,
    info VARCHAR(100),
    date_next_due DATETIME,
    payment_type_id INT,
    FOREIGN KEY (address_id) REFERENCES address(idaddress),
    FOREIGN KEY (customer_id) REFERENCES customer(idcustomer)
);

-- Job history table
CREATE TABLE job_history (
    idjob_history INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid TINYINT(1) NOT NULL DEFAULT 0,
    payment_type_id INT,
    FOREIGN KEY (job_id) REFERENCES jobs(idjob)
);
```

### 5. Run the Application

**Development mode:**
```bash
python app.py
```

**Production mode (with Gunicorn):**
```bash
gunicorn app:app
```

The application will be available at `http://localhost:5000`

## Application Routes

### Dashboard & Navigation
- `/` - Dashboard with due jobs, unpaid earnings, and job list
- `/stats` - Statistics and analytics with charts
- `/admin` - Admin settings for zone management

### Customer Routes
- `/customers` - List all customers
- `/customers/add` - Add a new customer
- `/customers/<id>` - View customer details
- `/customers/<id>/edit` - Edit customer information
- `/customers/<id>/delete` - Delete a customer (POST)
- `/customers/<customer_id>/invoice-address/add` - Add invoice address (POST)

### Job Routes
- `/jobs` - List all jobs
- `/jobs/add` - Add a new job (with or without customer)
- `/jobs/<id>` - View job details
- `/jobs/<id>/edit` - Edit job information
- `/jobs/<id>/delete` - Delete a job (POST)
- `/jobs/<id>/complete` - Mark job as complete (POST)
- `/jobs/<id>/add-customer` - Add customer to existing job
- `/jobs/due` - View all due/overdue jobs
- `/customers/<customer_id>/jobs/add` - Add job for specific customer (POST)

### Payment Routes
- `/payments/unpaid` - View all unpaid completed jobs
- `/payments/<history_id>/mark-paid` - Mark job as paid (POST)

### Admin Routes
- `/admin` - Admin settings page
- `/admin/zones/add` - Add new zone (POST)
- `/admin/zones/<id>/delete` - Delete zone (POST)

### API Routes
- `/api/customers` - JSON API endpoint for all customers

## Project Structure

```
WNv2/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .env                        # Environment variables (not in git)
├── .gitignore                  # Git ignore rules
└── templates/                  # HTML templates
    ├── base.html              # Base template with navigation
    ├── dashboard.html         # Dashboard page
    ├── stats.html             # Statistics page
    ├── customers/              # Customer templates
    │   ├── customers.html
    │   ├── add_customer.html
    │   ├── edit_customer.html
    │   └── detail.html
    ├── jobs/                   # Job templates
    │   ├── list.html
    │   ├── add.html
    │   ├── edit.html
    │   ├── detail.html
    │   ├── due.html
    │   └── add_customer.html
    ├── payments/               # Payment templates
    │   └── unpaid.html
    └── admin/                  # Admin templates
        └── settings.html
```

## Key Features Explained

### Job Management
- Jobs can be created with or without customers
- Jobs include address information (house number, street, postcode)
- Jobs are assigned to zones for geographic organization
- Frequency is stored in days (user inputs weeks, converted automatically)
- Jobs can be marked as complete with payment status tracking

### Zone System
- Zones organize jobs geographically
- Admin can add/delete zones
- Zone statistics shown in analytics
- Jobs can be filtered by zone on dashboard

### Payment Tracking
- When jobs are completed, payment status is recorded
- Unpaid jobs are tracked separately
- Payment history is maintained in job_history table
- Statistics show theoretical vs actual earnings

### Customer Management
- Surname is optional (system-wide)
- Customers can have separate invoice addresses
- Phone number validation (no spaces, digits only)
- Customers can be linked to jobs after job creation

## Deployment

### Production Considerations

1. **Update app.py for production:**
```python
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
```

2. **Add Gunicorn to requirements.txt:**
```
gunicorn==21.2.0
```

3. **Create Procfile (for Heroku/Railway):**
```
web: gunicorn app:app
```

### Recommended Hosting Platforms
- **Railway**: Easy deployment from GitHub
- **Render**: Free tier available
- **PythonAnywhere**: Good for beginners
- **Heroku**: Reliable but paid plans only

### Environment Variables for Production
- `DATABASE_URL`: Your production database connection string
- `SECRET_KEY`: Strong random secret key (use `secrets.token_hex(32)`)
- `PORT`: Port number (usually set by hosting platform)

## Development Notes

- The application uses SQLAlchemy ORM for database operations
- All timestamps are handled automatically
- Flash messages provide user feedback
- Search functionality available on list pages
- Dark mode CSS included in base template
- First column in all tables is bold
- Table headings are underlined
- Zone dropdowns fetch from database and display zone names

## Security Considerations

- Never commit `.env` file to version control
- Use strong SECRET_KEY in production
- Validate all user inputs
- Use HTTPS in production
- Consider adding authentication/authorization for admin routes
- Sanitize database queries (SQLAlchemy handles this)

## Future Enhancements

- Mobile app API endpoints for worker tracking
- User authentication and authorization
- Email notifications
- Export functionality (CSV/PDF)
- Advanced reporting and analytics
- Multi-organization support

## License

[Your License Here]

## Support

For issues or questions, please [create an issue](https://github.com/yourusername/WNv2/issues) or contact support.
