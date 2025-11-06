from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 
    'mysql+pymysql://username:password@localhost/dbname')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

# Routes
@app.route('/')
def dashboard():
    """Home page dashboard"""
    try:
        total_customers = Customer.query.count()
        recent_customers = Customer.query.order_by(Customer.timestamp.desc()).limit(5).all()
        return render_template('dashboard.html', 
                             total_customers=total_customers,
                             recent_customers=recent_customers)
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        return render_template('dashboard.html', 
                             total_customers=0,
                             recent_customers=[])

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
                surname=request.form.get('surname'),
                email=request.form.get('email'),
                telephone=telephone
            )
            db.session.add(customer)
            db.session.commit()
            flash('Customer added successfully!', 'success')
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
            customer.surname = request.form.get('surname')
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
        return render_template('customers/detail.html', customer=customer, jobs=jobs)
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

@app.route('/customers/<int:customer_id>/jobs/add', methods=['POST'])
def add_job(customer_id):
    """Add a new job for a customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
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
        
        job = Job(
            customer_id=customer_id,
            price=price,
            frequency=frequency_days,  # Store as days in database
            address_id=address_id,
            zone_id=int(request.form.get('zone_id')) if request.form.get('zone_id') else None,
            info=request.form.get('info'),
            payment_type_id=int(request.form.get('payment_type_id')) if request.form.get('payment_type_id') else None
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
        return render_template('jobs/list.html', jobs=jobs)
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        return render_template('jobs/list.html', jobs=[])

@app.route('/jobs/<int:id>')
def job_detail(id):
    """Display job detail view"""
    try:
        job = Job.query.get_or_404(id)
        return render_template('jobs/detail.html', job=job)
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
            job.zone_id = int(request.form.get('zone_id')) if request.form.get('zone_id') else None
            job.info = request.form.get('info')
            job.payment_type_id = int(request.form.get('payment_type_id')) if request.form.get('payment_type_id') else None
            
            db.session.commit()
            flash('Job updated successfully!', 'success')
            return redirect(url_for('job_detail', id=job.idjob))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating job: {str(e)}', 'error')
    
    return render_template('jobs/edit.html', job=job)

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

