from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 
    'mysql+pymysql://username:password@localhost/dbname')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

PAYMENT_TYPES = [
    {'id': 1, 'label': 'Cash'},
    {'id': 2, 'label': 'Card'},
    {'id': 3, 'label': 'Bank Transfer'}
]
PAYMENT_TYPE_MAP = {item['id']: item['label'] for item in PAYMENT_TYPES}


def parse_payment_type_id(raw_value):
    """Convert raw form value into a valid payment type id or None."""
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value in PAYMENT_TYPE_MAP else None

# Customer Model
class Customer(db.Model):
    __tablename__ = 'customer'
    
    idcustomer = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, nullable=True)
    address_id = db.Column(db.Integer, nullable=True)
    forename = db.Column(db.String(45), nullable=True)
    surname = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    email = db.Column(db.String(45), nullable=True)
    telephone = db.Column(db.Integer, nullable=True)
    
    def to_dict(self):
        return {
            'idcustomer': self.idcustomer,
            'org_id': self.org_id,
            'address_id': self.address_id,
            'forename': self.forename,
            'surname': self.surname,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'email': self.email,
            'telephone': self.telephone
        }

# Address Model
class Address(db.Model):
    __tablename__ = 'address'
    
    idaddress = db.Column(db.Integer, primary_key=True, autoincrement=True)
    house_num_name = db.Column(db.String(100), nullable=True)
    street_name = db.Column(db.String(100), nullable=True)
    postcode = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.String(100), nullable=True)
    longitude = db.Column(db.String(100), nullable=True)
    
    def to_dict(self):
        return {
            'idaddress': self.idaddress,
            'house_num_name': self.house_num_name,
            'street_name': self.street_name,
            'postcode': self.postcode,
            'latitude': self.latitude,
            'longitude': self.longitude
        }

# Zone Model
class Zone(db.Model):
    __tablename__ = 'zone'
    
    idzone = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    
    def to_dict(self):
        return {
            'idzone': self.idzone,
            'org_id': self.org_id,
            'name': self.name
        }

# Job Model
class Job(db.Model):
    __tablename__ = 'jobs'
    
    idjob = db.Column(db.Integer, primary_key=True, autoincrement=True)
    price = db.Column(db.Numeric(10, 2), nullable=True)
    dateLastDone = db.Column(db.Date, nullable=True)
    frequency = db.Column(db.Integer, nullable=True)
    org_id = db.Column(db.Integer, nullable=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.idaddress'), nullable=True)
    zone_id = db.Column(db.Integer, nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.idcustomer'), nullable=True)
    info = db.Column(db.String(100), nullable=True)
    date_next_due = db.Column(db.DateTime, nullable=True)
    payment_type_id = db.Column(db.Integer, nullable=True)
    
    # Relationships
    customer = db.relationship('Customer', backref='jobs')
    address = db.relationship('Address', backref='jobs')
    
    def to_dict(self):
        return {
            'idjob': self.idjob,
            'price': float(self.price) if self.price else None,
            'dateLastDone': self.dateLastDone.strftime('%Y-%m-%d') if self.dateLastDone else None,
            'frequency': self.frequency,
            'org_id': self.org_id,
            'address_id': self.address_id,
            'zone_id': self.zone_id,
            'customer_id': self.customer_id,
            'info': self.info,
            'date_next_due': self.date_next_due.strftime('%Y-%m-%d %H:%M:%S') if self.date_next_due else None,
            'payment_type_id': self.payment_type_id
        }

# Job History Model
class JobHistory(db.Model):
    __tablename__ = 'job_history'
    
    idjob_history = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.idjob'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    paid = db.Column(db.Boolean, nullable=False, default=False)
    payment_type_id = db.Column(db.Integer, nullable=True)
    
    # Relationships
    job = db.relationship('Job', backref='history')
    
    def to_dict(self):
        return {
            'idjob_history': self.idjob_history,
            'job_id': self.job_id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'paid': self.paid,
            'payment_type_id': self.payment_type_id
        }


def build_due_condition(reference_time):
    """Return SQLAlchemy filter condition for jobs that should appear as due."""
    return or_(
        Job.date_next_due <= reference_time,
        and_(Job.date_next_due.is_(None), Job.dateLastDone.is_(None))
    )


def build_schedule_condition():
    """Return filter condition for jobs that should appear in the schedule view."""
    return or_(
        Job.frequency.isnot(None),
        Job.dateLastDone.is_(None)
    )


# Routes
@app.route('/')
def dashboard():
    """Home page dashboard"""
    try:
        from datetime import datetime
        
        # Count due/overdue jobs
        today = datetime.now()
        due_jobs_count = Job.query.filter(
            build_due_condition(today)
        ).count()
        
        # Calculate unpaid earnings based on completed but unpaid job history entries
        unpaid_earnings = db.session.query(
            db.func.sum(db.func.coalesce(Job.price, 0))
        ).join(
            JobHistory, Job.idjob == JobHistory.job_id
        ).filter(
            JobHistory.paid == False
        ).scalar() or 0
        unpaid_earnings = float(unpaid_earnings)
        
        # Get jobs ordered by due date (jobs with no date first, then by date)
        jobs_by_due = Job.query.filter(
            build_schedule_condition()
        ).order_by(
            db.case(
                (Job.date_next_due.is_(None), 0),  # Put NULL dates first (0 comes before 1)
                else_=1
            ),
            Job.date_next_due.asc()
        ).all()
        
        # Calculate days until due for each job and get unique zones
        jobs_with_overdue = []
        zones_dict = {}
        today_date = today.date()
        for job in jobs_by_due:
            if job.date_next_due:
                days_until_due = (job.date_next_due.date() - today_date).days
            else:
                days_until_due = None
            
            if job.zone_id:
                # Get zone object if not already fetched
                if job.zone_id not in zones_dict:
                    zone = Zone.query.get(job.zone_id)
                    zones_dict[job.zone_id] = zone
            
            jobs_with_overdue.append({
                'job': job,
                'days_until_due': days_until_due
            })
        
        # Get all zones for the filter dropdown
        all_zones = Zone.query.order_by(Zone.name).all()
        
        return render_template('dashboard.html', 
                             due_jobs_count=due_jobs_count,
                             unpaid_earnings=unpaid_earnings,
                             jobs_by_due=jobs_with_overdue,
                             zones=all_zones)
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        all_zones = Zone.query.order_by(Zone.name).all()
        return render_template('dashboard.html', 
                             due_jobs_count=0,
                             unpaid_earnings=0,
                             jobs_by_due=[],
                             zones=all_zones)

@app.route('/customers')
def customers():
    """Display all customers"""
    try:
        customers_list = Customer.query.order_by(Customer.timestamp.desc()).all()
        return render_template('customers/customers.html', customers=customers_list)
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        return render_template('customers/customers.html', customers=[])

@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    """Add a new customer"""
    if request.method == 'POST':
        try:
            # Validate telephone number (no spaces)
            telephone = request.form.get('telephone')
            if telephone:
                telephone = telephone.strip()
                if ' ' in telephone:
                    flash('Telephone number cannot contain spaces. Please enter numbers only.', 'error')
                    return render_template('customers/add_customer.html')
                try:
                    telephone = int(telephone)
                except ValueError:
                    flash('Telephone number must contain only digits.', 'error')
                    return render_template('customers/add_customer.html')
            else:
                telephone = None
            
            customer = Customer(
                forename=request.form.get('forename'),
                surname=request.form.get('surname') or None,
                email=request.form.get('email'),
                telephone=telephone
            )
            db.session.add(customer)
            db.session.commit()
            flash('Customer added successfully!', 'success')
            
            # Check if we should return to job's add customer page
            return_to_job = request.args.get('return_to_job')
            if return_to_job:
                return redirect(url_for('add_customer_to_job', id=return_to_job))
            
            # Redirect to customer detail view instead of customers list
            return redirect(url_for('customer_detail', id=customer.idcustomer))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding customer: {str(e)}', 'error')
    
    return render_template('customers/add_customer.html')

@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
def edit_customer(id):
    """Edit an existing customer"""
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Validate telephone number (no spaces)
            telephone = request.form.get('telephone')
            if telephone:
                telephone = telephone.strip()
                if ' ' in telephone:
                    flash('Telephone number cannot contain spaces. Please enter numbers only.', 'error')
                    invoice_address = None
                    if customer.address_id:
                        invoice_address = Address.query.get(customer.address_id)
                    return render_template('customers/edit_customer.html', customer=customer, invoice_address=invoice_address)
                try:
                    telephone = int(telephone)
                except ValueError:
                    flash('Telephone number must contain only digits.', 'error')
                    invoice_address = None
                    if customer.address_id:
                        invoice_address = Address.query.get(customer.address_id)
                    return render_template('customers/edit_customer.html', customer=customer, invoice_address=invoice_address)
            else:
                telephone = None
            
            customer.forename = request.form.get('forename')
            customer.surname = request.form.get('surname') or None
            customer.email = request.form.get('email')
            customer.telephone = telephone
            
            db.session.commit()
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customer_detail', id=customer.idcustomer))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'error')
    
    # Get invoice address if exists
    invoice_address = None
    if customer.address_id:
        invoice_address = Address.query.get(customer.address_id)
    
    return render_template('customers/edit_customer.html', customer=customer, invoice_address=invoice_address)

@app.route('/customers/<int:customer_id>/invoice-address/add', methods=['POST'])
def add_invoice_address(customer_id):
    """Add or update invoice address for a customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        # Create or find address
        if request.form.get('house_number') and request.form.get('street'):
            # Check if address already exists
            existing_address = Address.query.filter_by(
                house_num_name=request.form.get('house_number'),
                street_name=request.form.get('street'),
                postcode=request.form.get('postcode')
            ).first()
            
            if existing_address:
                address_id = existing_address.idaddress
            else:
                # Create new address
                address = Address(
                    house_num_name=request.form.get('house_number'),
                    street_name=request.form.get('street'),
                    postcode=request.form.get('postcode'),
                    latitude=None,
                    longitude=None
                )
                db.session.add(address)
                db.session.flush()  # Get the address ID
                address_id = address.idaddress
            
            # Update customer's invoice address
            customer.address_id = address_id
            db.session.commit()
            flash('Invoice address updated successfully!', 'success')
        else:
            flash('Please fill in all required address fields', 'error')
        
        return redirect(url_for('edit_customer', id=customer_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating invoice address: {str(e)}', 'error')
        return redirect(url_for('edit_customer', id=customer_id))

@app.route('/customers/<int:id>')
def customer_detail(id):
    """Display customer detail view"""
    try:
        customer = Customer.query.get_or_404(id)
        jobs = Job.query.filter_by(customer_id=id).order_by(Job.idjob.desc()).all()
        # Get zones for the add job modal
        zones = Zone.query.order_by(Zone.name).all()
        return render_template(
            'customers/detail.html',
            customer=customer,
            jobs=jobs,
            zones=zones
        )
    except Exception as e:
        flash(f'Error loading customer: {str(e)}', 'error')
        return redirect(url_for('customers'))

@app.route('/customers/<int:id>/delete', methods=['POST'])
def delete_customer(id):
    """Delete a customer"""
    customer = Customer.query.get_or_404(id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'error')
    return redirect(url_for('customers'))

@app.route('/jobs/add', methods=['GET', 'POST'])
def add_job():
    """Add a new job (with or without customer)"""
    if request.method == 'POST':
        try:
            # Customer ID is optional
            customer_id = None
            if request.form.get('customer_id'):
                try:
                    customer_id = int(request.form.get('customer_id'))
                    # Verify customer exists if provided
                    Customer.query.get_or_404(customer_id)
                except (ValueError, Exception):
                    customer_id = None
            
            # Create or find address
            address_id = None
            if request.form.get('house_number') and request.form.get('street'):
                # Check if address already exists
                existing_address = Address.query.filter_by(
                    house_num_name=request.form.get('house_number'),
                    street_name=request.form.get('street'),
                    postcode=request.form.get('postcode')
                ).first()
                
                if existing_address:
                    address_id = existing_address.idaddress
                else:
                    # Create new address
                    address = Address(
                        house_num_name=request.form.get('house_number'),
                        street_name=request.form.get('street'),
                        postcode=request.form.get('postcode'),
                        latitude=None,
                        longitude=None
                    )
                    db.session.add(address)
                    db.session.flush()  # Get the address ID
                    address_id = address.idaddress
            
            # Parse price
            price = None
            if request.form.get('price'):
                try:
                    price = float(request.form.get('price'))
                except ValueError:
                    price = None
            
            # Convert frequency from weeks to days (since database stores in days)
            frequency_weeks = None
            if request.form.get('frequency'):
                try:
                    frequency_weeks = int(request.form.get('frequency'))
                except ValueError:
                    frequency_weeks = None
            
            frequency_days = frequency_weeks * 7 if frequency_weeks else None

            zone_id_raw = request.form.get('zone_id')
            if not zone_id_raw:
                flash('Please select a zone for the job.', 'error')
                return redirect(url_for('add_job'))
            try:
                zone_id = int(zone_id_raw)
                zone = Zone.query.get(zone_id)
                if not zone:
                    raise ValueError('Invalid zone')
            except (ValueError, TypeError):
                flash('Invalid zone selected.', 'error')
                return redirect(url_for('add_job'))
            
            job = Job(
                customer_id=customer_id,
                price=price,
                frequency=frequency_days,  # Store as days in database
                address_id=address_id,
                zone_id=zone_id,
                info=request.form.get('info')
            )
            db.session.add(job)
            db.session.commit()
            flash('Job added successfully!', 'success')
            return redirect(url_for('job_detail', id=job.idjob))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding job: {str(e)}', 'error')
    
    # GET request - show form
    # Get all customers for dropdown
    customers = Customer.query.order_by(Customer.surname, Customer.forename).all()
    # Get all zones for dropdown
    zones = Zone.query.order_by(Zone.name).all()
    return render_template('jobs/add.html', customers=customers, zones=zones)

@app.route('/customers/<int:customer_id>/jobs/add', methods=['POST'])
def add_job_for_customer(customer_id):
    """Add a new job for a specific customer (legacy route for customer detail page)"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        zones = Zone.query.order_by(Zone.name).all()
        
        # Create or find address
        address_id = None
        if request.form.get('house_number') and request.form.get('street'):
            # Check if address already exists
            existing_address = Address.query.filter_by(
                house_num_name=request.form.get('house_number'),
                street_name=request.form.get('street'),
                postcode=request.form.get('postcode')
            ).first()
            
            if existing_address:
                address_id = existing_address.idaddress
            else:
                # Create new address
                address = Address(
                    house_num_name=request.form.get('house_number'),
                    street_name=request.form.get('street'),
                    postcode=request.form.get('postcode'),
                    latitude=None,  # Can be added later if needed
                    longitude=None   # Can be added later if needed
                )
                db.session.add(address)
                db.session.flush()  # Get the address ID
                address_id = address.idaddress
        
        # Parse price
        price = None
        if request.form.get('price'):
            try:
                price = float(request.form.get('price'))
            except ValueError:
                price = None
        
        # Convert frequency from weeks to days (since database stores in days)
        frequency_weeks = None
        if request.form.get('frequency'):
            try:
                frequency_weeks = int(request.form.get('frequency'))
            except ValueError:
                frequency_weeks = None
        
        frequency_days = frequency_weeks * 7 if frequency_weeks else None

        zone_id_raw = request.form.get('zone_id')
        if not zone_id_raw:
            flash('Please select a zone for the job.', 'error')
            return redirect(url_for('customer_detail', id=customer_id))
        try:
            zone_id = int(zone_id_raw)
            zone = Zone.query.get(zone_id)
            if not zone:
                raise ValueError('Invalid zone')
        except (ValueError, TypeError):
            flash('Invalid zone selected.', 'error')
            return redirect(url_for('customer_detail', id=customer_id))

        job = Job(
            customer_id=customer_id,
            price=price,
            frequency=frequency_days,  # Store as days in database
            address_id=address_id,
            zone_id=zone_id,
            info=request.form.get('info')
        )
        db.session.add(job)
        db.session.commit()
        flash('Job added successfully!', 'success')
        return redirect(url_for('customer_detail', id=customer_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding job: {str(e)}', 'error')
        return redirect(url_for('customer_detail', id=customer_id))

@app.route('/jobs')
def jobs_list():
    """Display all jobs"""
    try:
        jobs = Job.query.order_by(Job.idjob.desc()).all()
        zones = Zone.query.order_by(Zone.name).all()
        zones_by_id = {zone.idzone: zone for zone in zones}
        return render_template('jobs/list.html', jobs=jobs, zones_by_id=zones_by_id)
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        return render_template('jobs/list.html', jobs=[], zones_by_id={})

@app.route('/jobs/<int:id>')
def job_detail(id):
    """Display job detail view"""
    try:
        job = Job.query.options(
            joinedload(Job.customer),
            joinedload(Job.address)
        ).filter_by(idjob=id).first_or_404()
        # Get job history (completions)
        job_history = JobHistory.query.filter_by(job_id=job.idjob).order_by(JobHistory.timestamp.desc()).all()
        # Get zone if zone_id is set
        zone = None
        if job.zone_id:
            zone = Zone.query.get(job.zone_id)
        return render_template(
            'jobs/detail.html',
            job=job,
            job_history=job_history,
            zone=zone,
            payment_types=PAYMENT_TYPES,
            payment_type_map=PAYMENT_TYPE_MAP
        )
    except Exception as e:
        flash(f'Error loading job: {str(e)}', 'error')
        return redirect(url_for('jobs_list'))

@app.route('/jobs/<int:id>/edit', methods=['GET', 'POST'])
def edit_job(id):
    """Edit an existing job"""
    job = Job.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Parse price
            price = None
            if request.form.get('price'):
                try:
                    price = float(request.form.get('price'))
                except ValueError:
                    price = None
            
            # Convert frequency from weeks to days
            frequency_weeks = None
            if request.form.get('frequency'):
                try:
                    frequency_weeks = int(request.form.get('frequency'))
                except ValueError:
                    frequency_weeks = None
            
            frequency_days = frequency_weeks * 7 if frequency_weeks else None
            
            # Update address if provided
            if request.form.get('house_number') and request.form.get('street'):
                existing_address = Address.query.filter_by(
                    house_num_name=request.form.get('house_number'),
                    street_name=request.form.get('street'),
                    postcode=request.form.get('postcode')
                ).first()
                
                if existing_address:
                    address_id = existing_address.idaddress
                else:
                    address = Address(
                        house_num_name=request.form.get('house_number'),
                        street_name=request.form.get('street'),
                        postcode=request.form.get('postcode'),
                        latitude=None,
                        longitude=None
                    )
                    db.session.add(address)
                    db.session.flush()
                    address_id = address.idaddress
                
                job.address_id = address_id
            
            job.price = price
            job.frequency = frequency_days
            if job.frequency is None:
                job.date_next_due = None
            zone_id = request.form.get('zone_id')
            job.zone_id = int(zone_id) if zone_id and zone_id != '' else None
            job.info = request.form.get('info')
            job.payment_type_id = parse_payment_type_id(request.form.get('payment_type_id'))
            
            db.session.commit()
            flash('Job updated successfully!', 'success')
            return redirect(url_for('job_detail', id=job.idjob))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating job: {str(e)}', 'error')
    
    # Get all zones for dropdown
    zones = Zone.query.order_by(Zone.name).all()
    return render_template('jobs/edit.html', job=job, zones=zones)

@app.route('/jobs/<int:id>/delete', methods=['POST'])
def delete_job(id):
    """Delete a job"""
    job = Job.query.get_or_404(id)
    try:
        db.session.delete(job)
        db.session.commit()
        flash('Job deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting job: {str(e)}', 'error')
    return redirect(url_for('jobs_list'))

@app.route('/jobs/<int:id>/complete', methods=['POST'])
def complete_job(id):
    """Mark a job as completed and update dates"""
    job = Job.query.get_or_404(id)
    
    try:
        today = datetime.now().date()
        paid = request.form.get('paid') == 'true'
        payment_type_value = parse_payment_type_id(request.form.get('payment_type_id'))

        if paid and payment_type_value is None:
            flash('Please select how the job was paid.', 'error')
            return redirect(url_for('job_detail', id=job.idjob))
        if not paid:
            payment_type_value = None
        
        # Update job dates
        job.dateLastDone = today
        
        # Calculate next due date (frequency is stored in days)
        if job.frequency:
            job.date_next_due = datetime.now() + timedelta(days=job.frequency)
        else:
            job.date_next_due = None
        
        # Create job history entry
        job_history = JobHistory(
            job_id=job.idjob,
            timestamp=datetime.now(),
            paid=paid,
            payment_type_id=payment_type_value
        )
        
        db.session.add(job_history)
        db.session.commit()
        
        payment_status = "Paid" if paid else "Unpaid"
        flash(f'Job marked as complete! Payment: {payment_status}', 'success')
        return redirect(url_for('jobs_due'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing job: {str(e)}', 'error')
        return redirect(url_for('job_detail', id=job.idjob))


@app.route('/jobs/completed')
def jobs_completed():
    """Display all completed job entries with filtering and sorting options."""
    try:
        customer_id = request.args.get('customer_id') or None
        zone_id = request.args.get('zone_id') or None
        paid_filter = request.args.get('paid', 'all')
        payment_type_raw = request.args.get('payment_type_id') or None
        payment_type_id = parse_payment_type_id(payment_type_raw) if payment_type_raw else None
        sort_param = request.args.get('sort', 'date_desc')
        search_term = request.args.get('search', '').strip()

        query = JobHistory.query.options(
            joinedload(JobHistory.job).joinedload(Job.customer),
            joinedload(JobHistory.job).joinedload(Job.address)
        ).join(Job, JobHistory.job).outerjoin(Customer, Job.customer).outerjoin(Zone, Job.zone_id == Zone.idzone).outerjoin(Address, Job.address)

        if customer_id:
            try:
                customer_id_int = int(customer_id)
                query = query.filter(Job.customer_id == customer_id_int)
            except ValueError:
                pass

        if zone_id:
            try:
                zone_id_int = int(zone_id)
                query = query.filter(Job.zone_id == zone_id_int)
            except ValueError:
                pass

        if paid_filter == 'paid':
            query = query.filter(JobHistory.paid.is_(True))
        elif paid_filter == 'unpaid':
            query = query.filter(JobHistory.paid.is_(False))

        if payment_type_id is not None:
            query = query.filter(JobHistory.payment_type_id == payment_type_id)

        if search_term:
            like_term = f"%{search_term}%"
            query = query.filter(
                or_(
                    Job.info.ilike(like_term),
                    Address.house_num_name.ilike(like_term),
                    Address.street_name.ilike(like_term),
                    Address.postcode.ilike(like_term)
                )
            )

        if sort_param == 'date_asc':
            query = query.order_by(JobHistory.timestamp.asc())
        elif sort_param == 'customer_asc':
            query = query.order_by(Customer.surname.asc(), Customer.forename.asc(), JobHistory.timestamp.desc())
        elif sort_param == 'customer_desc':
            query = query.order_by(Customer.surname.desc(), Customer.forename.desc(), JobHistory.timestamp.desc())
        elif sort_param == 'zone_asc':
            query = query.order_by(Zone.name.asc(), JobHistory.timestamp.desc())
        elif sort_param == 'zone_desc':
            query = query.order_by(Zone.name.desc(), JobHistory.timestamp.desc())
        elif sort_param == 'paid_status':
            query = query.order_by(JobHistory.paid.desc(), JobHistory.timestamp.desc())
        else:
            query = query.order_by(JobHistory.timestamp.desc())

        histories = query.all()
        customers = Customer.query.order_by(Customer.surname, Customer.forename).all()
        zones = Zone.query.order_by(Zone.name).all()

        filters = {
            'customer_id': customer_id or '',
            'zone_id': zone_id or '',
            'paid': paid_filter,
            'payment_type_id': payment_type_raw if payment_type_id is not None else '',
            'sort': sort_param,
            'search': search_term
        }

        return render_template(
            'jobs/completed.html',
            histories=histories,
            customers=customers,
            zones=zones,
            payment_types=PAYMENT_TYPES,
            payment_type_map=PAYMENT_TYPE_MAP,
            filters=filters
        )
    except Exception as e:
        flash(f'Error loading completed jobs: {str(e)}', 'error')
        return render_template(
            'jobs/completed.html',
            histories=[],
            customers=[],
            zones=[],
            payment_types=PAYMENT_TYPES,
            payment_type_map=PAYMENT_TYPE_MAP,
            filters={
                'customer_id': '',
                'zone_id': '',
                'paid': 'all',
                'payment_type_id': '',
                'sort': 'date_desc',
                'search': ''
            }
        )


@app.route('/jobs/due')
def jobs_due():
    """Display all jobs that are due or overdue"""
    try:
        today = datetime.now()
        zones = Zone.query.order_by(Zone.name).all()
        zones_by_id = {zone.idzone: zone for zone in zones}
        due_jobs = Job.query.filter(
            build_schedule_condition()
        ).order_by(Job.date_next_due.asc()).all()
        
        # Calculate days until due for each job
        jobs_with_overdue = []
        today_date = today.date()
        for job in due_jobs:
            if job.date_next_due:
                days_until_due = (job.date_next_due.date() - today_date).days
            else:
                days_until_due = None
            
            jobs_with_overdue.append({
                'job': job,
                'days_until_due': days_until_due
            })
        
        return render_template('jobs/due.html', jobs=jobs_with_overdue, zones_by_id=zones_by_id)
    except Exception as e:
        flash(f'Error loading due jobs: {str(e)}', 'error')
        return render_template('jobs/due.html', jobs=[], zones_by_id={})

@app.route('/stats')
def stats():
    """Display statistics and graphs"""
    try:
        total_customers = Customer.query.count()
        total_jobs = Job.query.count()
        
        # Customer statistics
        customers_with_jobs = db.session.query(Customer).join(Job).distinct().count()
        customers_without_jobs = total_customers - customers_with_jobs
        
        # Job statistics
        jobs_with_price = Job.query.filter(Job.price.isnot(None)).count()
        total_revenue = db.session.query(db.func.sum(Job.price)).scalar() or 0
        
        # Theoretical earnings (sum of all job prices)
        theoretical_earnings = db.session.query(db.func.sum(Job.price)).scalar() or 0
        
        # Actual earnings (from paid job_history entries)
        actual_earnings = 0
        if JobHistory.query.count() > 0:
            actual_earnings = db.session.query(
                db.func.sum(Job.price)
            ).join(
                JobHistory, Job.idjob == JobHistory.job_id
            ).filter(JobHistory.paid == True).scalar() or 0
        
        # Earnings by month (actual paid earnings)
        earnings_by_month = []
        if JobHistory.query.count() > 0:
            earnings_by_month = db.session.query(
                db.func.date_format(JobHistory.timestamp, '%Y-%m').label('month'),
                db.func.sum(Job.price).label('earnings')
            ).join(Job, JobHistory.job_id == Job.idjob).filter(
                JobHistory.paid == True
            ).group_by('month').order_by('month').all()
        
        # Frequency distribution
        frequency_data = db.session.query(
            db.case(
                (Job.frequency == None, 'Not Set'),
                (Job.frequency <= 7, 'Weekly'),
                (Job.frequency <= 14, 'Bi-weekly'),
                (Job.frequency <= 30, 'Monthly'),
                else_='Other'
            ).label('frequency_category'),
            db.func.count(Job.idjob).label('count')
        ).group_by('frequency_category').all()
        
        # Jobs by month (if timestamp exists, using idjob as proxy for creation order)
        recent_jobs = Job.query.order_by(Job.idjob.desc()).limit(12).all()
        
        # Zone-based statistics
        zone_stats = []
        zones = Zone.query.all()
        for zone in zones:
            zone_jobs = Job.query.filter_by(zone_id=zone.idzone).all()
            zone_revenue = sum(float(job.price) if job.price else 0 for job in zone_jobs)
            zone_job_count = len(zone_jobs)
            zone_stats.append({
                'zone_name': zone.name,
                'revenue': zone_revenue,
                'job_count': zone_job_count
            })
        
        # Zone distribution (for pie chart)
        zone_distribution = []
        for zone in zones:
            job_count = Job.query.filter_by(zone_id=zone.idzone).count()
            if job_count > 0:
                zone_distribution.append({
                    'zone_name': zone.name,
                    'job_count': job_count
                })

        # Payment type distribution by zone (based on completed jobs)
        base_payment_counts = {pt['id']: 0 for pt in PAYMENT_TYPES}
        zone_payment_counts = {
            zone.name: base_payment_counts.copy()
            for zone in zones
        }

        payment_query = db.session.query(
            Zone.name.label('zone_name'),
            JobHistory.payment_type_id
        ).join(Job, JobHistory.job_id == Job.idjob)\
         .join(Zone, Job.zone_id == Zone.idzone, isouter=True)\
         .filter(JobHistory.payment_type_id.isnot(None))

        for result in payment_query:
            zone_name = result.zone_name or 'No Zone'
            if zone_name not in zone_payment_counts:
                zone_payment_counts[zone_name] = base_payment_counts.copy()
            if result.payment_type_id in PAYMENT_TYPE_MAP:
                zone_payment_counts[zone_name][result.payment_type_id] += 1

        zone_payment_labels = sorted(
            [name for name in zone_payment_counts.keys() if name != 'No Zone']
        )
        if 'No Zone' in zone_payment_counts:
            zone_payment_labels.append('No Zone')

        zone_payment_datasets = []
        for payment in PAYMENT_TYPES:
            dataset_values = [
                zone_payment_counts[zone_name][payment['id']]
                for zone_name in zone_payment_labels
            ]
            zone_payment_datasets.append({
                'label': payment['label'],
                'data': dataset_values
            })
        
        # Weekly earnings (theoretical vs actual collected)
        # Get last 8 weeks of data
        from datetime import datetime, timedelta
        weekly_earnings = []
        today = datetime.now()
        for i in range(7, -1, -1):  # Last 8 weeks
            week_start = today - timedelta(weeks=i+1)
            week_end = today - timedelta(weeks=i)
            
            # Theoretical earnings (all jobs completed in this week)
            theoretical_week = db.session.query(
                db.func.sum(Job.price)
            ).join(
                JobHistory, Job.idjob == JobHistory.job_id
            ).filter(
                JobHistory.timestamp >= week_start,
                JobHistory.timestamp < week_end
            ).scalar() or 0
            
            # Actual collected (paid jobs in this week)
            actual_week = db.session.query(
                db.func.sum(Job.price)
            ).join(
                JobHistory, Job.idjob == JobHistory.job_id
            ).filter(
                JobHistory.timestamp >= week_start,
                JobHistory.timestamp < week_end,
                JobHistory.paid == True
            ).scalar() or 0
            
            week_label = week_start.strftime('%Y-%m-%d')
            weekly_earnings.append({
                'week': week_label,
                'theoretical': float(theoretical_week),
                'actual': float(actual_week)
            })
        
        stats_data = {
            'total_customers': total_customers,
            'total_jobs': total_jobs,
            'customers_with_jobs': customers_with_jobs,
            'customers_without_jobs': customers_without_jobs,
            'jobs_with_price': jobs_with_price,
            'total_revenue': float(total_revenue),
            'theoretical_earnings': float(theoretical_earnings),
            'actual_earnings': float(actual_earnings),
            'zone_stats': zone_stats,
            'zone_distribution': zone_distribution,
            'zone_payment_distribution': {
                'zones': zone_payment_labels,
                'datasets': zone_payment_datasets
            },
            'weekly_earnings': weekly_earnings
        }
        
        return render_template('stats.html', stats=stats_data)
    except Exception as e:
        flash(f'Error loading statistics: {str(e)}', 'error')
        return render_template('stats.html', stats={
            'total_customers': 0,
            'total_jobs': 0,
            'customers_with_jobs': 0,
            'customers_without_jobs': 0,
            'jobs_with_price': 0,
            'total_revenue': 0,
            'theoretical_earnings': 0,
            'actual_earnings': 0,
            'zone_stats': [],
            'zone_distribution': [],
            'zone_payment_distribution': {
                'zones': [],
                'datasets': []
            },
            'weekly_earnings': []
        })

@app.route('/jobs/<int:id>/add-customer', methods=['GET', 'POST'])
def add_customer_to_job(id):
    """Add or update customer for an existing job"""
    job = Job.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id')
            if customer_id:
                customer_id = int(customer_id)
                # Verify customer exists
                Customer.query.get_or_404(customer_id)
                job.customer_id = customer_id
            else:
                job.customer_id = None
            
            db.session.commit()
            flash('Customer information updated successfully!', 'success')
            return redirect(url_for('job_detail', id=job.idjob))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'error')
    
    # GET request - show form
    customers = Customer.query.order_by(Customer.surname, Customer.forename).all()
    return render_template('jobs/add_customer.html', job=job, customers=customers)

@app.route('/admin')
def admin_settings():
    """Admin settings page"""
    zones = Zone.query.order_by(Zone.name).all()
    return render_template('admin/settings.html', zones=zones)

@app.route('/admin/zones/add', methods=['POST'])
def add_zone():
    """Add a new zone"""
    try:
        zone_name = request.form.get('zone_name')
        
        if not zone_name:
            flash('Zone name is required', 'error')
            return redirect(url_for('admin_settings'))
        
        zone = Zone(
            name=zone_name
        )
        db.session.add(zone)
        db.session.commit()
        flash('Zone added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding zone: {str(e)}', 'error')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/zones/<int:id>/delete', methods=['POST'])
def delete_zone(id):
    """Delete a zone"""
    zone = Zone.query.get_or_404(id)
    try:
        db.session.delete(zone)
        db.session.commit()
        flash('Zone deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting zone: {str(e)}', 'error')
    return redirect(url_for('admin_settings'))

@app.route('/payments/unpaid')
def unpaid_jobs():
    """Display all jobs that need to be paid"""
    try:
        # Get all job history entries that are unpaid
        unpaid_history = JobHistory.query.filter_by(paid=False).order_by(JobHistory.timestamp.desc()).all()
        
        unpaid_jobs_list = []
        for history in unpaid_history:
            job = Job.query.get(history.job_id)
            if job:
                customer_name = ""
                if job.customer:
                    customer_name = f"{job.customer.forename or ''} {job.customer.surname or ''}".strip()
                    if not customer_name:
                        customer_name = "No Name"
                else:
                    customer_name = "No Customer"
                
                unpaid_jobs_list.append({
                    'history_id': history.idjob_history,
                    'job_id': job.idjob,
                    'customer_name': customer_name,
                    'price': float(job.price) if job.price else 0,
                    'completion_time': history.timestamp,
                    'job': job,
                    'history': history
                })
        
        return render_template('payments/unpaid.html', unpaid_jobs=unpaid_jobs_list)
    except Exception as e:
        flash(f'Error loading unpaid jobs: {str(e)}', 'error')
        return render_template('payments/unpaid.html', unpaid_jobs=[])

@app.route('/payments/<int:history_id>/mark-paid', methods=['POST'])
def mark_job_paid(history_id):
    """Mark a job history entry as paid"""
    try:
        history = JobHistory.query.get_or_404(history_id)
        history.paid = True
        db.session.commit()
        flash('Payment recorded successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording payment: {str(e)}', 'error')
    
    return redirect(url_for('unpaid_jobs'))

@app.route('/api/customers')
def api_customers():
    """API endpoint to get all customers as JSON"""
    customers = Customer.query.all()
    return jsonify([customer.to_dict() for customer in customers])

# Error handler for better debugging
@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return f"<h1>Internal Server Error</h1><p>{str(error)}</p>", 500

if __name__ == '__main__':
    app.run(debug=True)

