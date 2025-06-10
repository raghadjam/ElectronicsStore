from datetime import date, datetime
from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
import mysql, re
from db import get_connection
from mysql.connector import Error 


app = Flask(__name__)
app.secret_key = '1220212'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    if request.method == 'POST':
        data = (
            request.form['product_id'],
            request.form['product_name'],
            request.form['category'],
            request.form['price'],
            request.form['stock_quantity'],
            request.form['stock_arrival_date']
        )
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Product (product_id, product_name, category, price, stock_quantity, stock_arrival_date) VALUES (%s, %s, %s, %s, %s, %s)",
            data
        )
        conn.commit()
        conn.close()
        return redirect(url_for('home'))
    return render_template('insert.html')

@app.route('/update', methods=['GET', 'POST'])
def update():
    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Product
            SET product_name=%s, category=%s, price=%s, stock_quantity=%s, stock_arrival_date=%s
            WHERE product_id=%s
        """, (
            request.form['product_name'],
            request.form['category'],
            request.form['price'],
            request.form['stock_quantity'],
            request.form['stock_arrival_date'],
            request.form['product_id']
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))
    return render_template('update.html')

@app.route('/delete', methods=['GET', 'POST'])
def delete():
    if request.method == 'POST':
        product_id = request.form['product_id']

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Get product details for archiving
            cursor.execute("SELECT product_id, product_name, category, price, stock_quantity, stock_arrival_date FROM Product WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()

            if not product:
                conn.close()
                # flash("Product not found.")
                return redirect(url_for('delete'))

            # Archive the product
            archive_data = product + (date.today(),)
            cursor.execute(
                "INSERT INTO Product_Archive (product_id, product_name, category, price, stock_quantity, stock_arrival_date, archived_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                archive_data
            )

            # Delete related entries from OrderDetails and PurchaseOrderDetails (to avoid foreign key constraint issues)
            cursor.execute("DELETE FROM OrderDetails WHERE product_id = %s", (product_id,))
            cursor.execute("DELETE FROM PurchaseOrderDetails WHERE product_id = %s", (product_id,))

            # Now delete the product from Product
            cursor.execute("DELETE FROM Product WHERE product_id = %s", (product_id,))

            # Commit and close the connection
            conn.commit()
            conn.close()

            # flash("Product successfully deleted and archived.")
            return redirect(url_for('home'))

        except mysql.connector.Error as err:
            if conn:
                conn.rollback()
                conn.close()
            # flash(f"Error: {err}")
            
            return redirect(url_for('delete'))

    return render_template('delete.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    products = []
    if request.method == 'POST':
        keyword = request.form['keyword']
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Product WHERE product_name LIKE %s OR category LIKE %s", (f"%{keyword}%", f"%{keyword}%"))
        products = cursor.fetchall()
        conn.close()
    return render_template('search.html', products=products)

@app.route('/retrieve')
def retrieve():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()
    conn.close()
    return render_template('retrieve.html', products=products)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/product')
def product():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, product_name, category, price, stock_quantity FROM Product")
    products = cursor.fetchall()
    conn.close()
    return render_template('product.html', products=products, logged_in='customer_id' in session)


@app.route('/customerlogin', methods=['GET', 'POST'])
def customerlogin():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        password = request.form['password'] 

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Customer WHERE customer_id = %s AND Customer_password = %s", (customer_id, password))
        customer = cursor.fetchone()
        conn.close()

        if customer:
            session['customer_id'] = customer_id # Store the customer_id in the session
            flash("Logged in successfully!", "success")
            return redirect(url_for('product')) # Redirect to home or a specific dashboard
        else:
            flash("Invalid ID or password", "error")
            return render_template('customerlogin.html', error="Invalid ID or password", logged_in=False)
            
    return render_template('customerlogin.html', logged_in='customer_id' in session)


@app.route('/profile')
def profile():
    # Check if customer_id is in session (i.e., user is logged in)
    if 'customer_id' not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('customerlogin'))  # Redirect to login if not logged in

    customer_id = session['customer_id']

    # Connect to MySQL database
    conn =get_connection()
    cursor = conn.cursor()

    # Get customer details
    cursor.execute("SELECT * FROM Customer WHERE customer_id = %s", (customer_id,))
    customer = cursor.fetchone()

    # Get total number of customers
    cursor.execute("SELECT COUNT(*) FROM Customer")
    total_customers = cursor.fetchone()[0]

    # Get total orders
    cursor.execute("SELECT SUM(order_count) FROM Customer")
    total_orders = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    if not customer:
        # If customer not found in DB, logout and redirect
        session.pop('customer_id', None)
        flash("User not found. Please log in again.", "error")
        return redirect(url_for('customerlogin'))

    return render_template('profile.html',
                           customer=customer,
                           total_customers=total_customers,
                           total_orders=total_orders)


# --- NEW: Logout Route ---
@app.route('/logout')
def logout():
    session.pop('customer_id', None) # Remove customer_id from session
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'customer_id' not in session:
        flash("Please log in to add items to your cart.", "info")
        return redirect(url_for('customerlogin'))

    customer_id = session['customer_id']
    product_id = request.form['product_id']
    print(product_id)
    quantity = 1 # Default quantity to 1 for each add to cart click

    if not product_id:
        flash("Invalid product selected.", "error")
        return redirect(url_for('product'))

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Get product price
        cursor.execute("SELECT price, product_name FROM Product WHERE product_id = %s", (product_id,))
        product_info = cursor.fetchone()
        if not product_info:
            flash("Product not found.", "error")
            return redirect(url_for('product'))
        
        product_price = product_info['price']

        # 2. Find or create a 'cart' order for the customer
        cursor.execute("SELECT order_id FROM `Order` WHERE customer_id = %s AND status = 'cart'", (customer_id,))
        current_cart_order = cursor.fetchone()
        order_id = None

        if current_cart_order:
            order_id = current_cart_order['order_id']
        else:
            # Create a new 'cart' order
            cursor.execute("INSERT INTO `Order` (customer_id, order_date, status) VALUES (%s, %s, %s)",
                           (customer_id, date.today(), 'cart'))
            conn.commit() # Commit to get the last inserted ID
            order_id = cursor.lastrowid # Get the ID of the newly created order

        # 3. Add product to OrderDetails (or update quantity if already exists)
        cursor.execute("SELECT order_id, quantity FROM OrderDetails WHERE order_id = %s AND product_id = %s",
                       (order_id, product_id))
        existing_item = cursor.fetchone()

        if existing_item:
            # Item already in cart, update quantity
            new_quantity = existing_item['quantity'] + quantity
            cursor.execute("UPDATE OrderDetails SET quantity = %s WHERE order_id = %s",
                           (new_quantity, existing_item['order_id']))
            flash(f"Added another {product_info['product_name']} to cart!", "success")
        else:
            # Add new item to cart
            cursor.execute("INSERT INTO OrderDetails (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                           (order_id, product_id, quantity, product_price))
            flash(f"{product_info['product_name']} added to cart!", "success")
        
        conn.commit()
        return redirect(url_for('cart'))

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")  

        if conn:
            conn.rollback()
        return redirect(url_for('product'))
    finally:
        if conn:
            conn.close()

@app.route('/cart')
def cart():
    if 'customer_id' not in session:
        flash("Please log in to view your cart.", "info")
        return redirect(url_for('customerlogin'))

    customer_id = session['customer_id']
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT order_id FROM `Order` WHERE customer_id = %s AND status = 'cart'", (customer_id,))
        current_cart_order = cursor.fetchone()

        cart_items = []
        total_price = 0.0

        if current_cart_order:
            order_id = current_cart_order['order_id']

            cursor.execute("""
                SELECT od.product_id, od.quantity, od.price_at_order, p.product_name
                FROM OrderDetails od
                JOIN Product p ON od.product_id = p.product_id
                WHERE od.order_id = %s
            """, (order_id,))

            cart_items = cursor.fetchall()
            total_price = sum(item['price_at_order'] * item['quantity'] for item in cart_items)

        return render_template('cart.html', cart_items=cart_items, total_price=total_price)

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        flash("Could not load cart at this time.", "error")
        return render_template('cart.html', cart_items=[], total_price=0)

    finally:
        if conn:
            conn.close()



@app.route('/managerlog', methods=['GET', 'POST'])
def managerlog():
    if request.method == 'POST':
        manager_id = request.form['manager_id']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if this ID belongs to a manager (someone who manages others)
        query = """
            SELECT * FROM Employee 
            WHERE employee_id = %s AND (
            emp_role = 'Manager' OR emp_role = 'Assistant Manager') 
            AND employee_id IN (
                SELECT DISTINCT manager_id FROM Employee WHERE manager_id IS NOT NULL
            )
        """
        cursor.execute(query, (manager_id,))
        manager = cursor.fetchone()
        cursor.close()
        conn.close()

        if manager:
            if password == '1234':  
                return redirect(url_for('manager', employee_id=manager_id))
            else:
                return redirect(url_for('managerlog'))
        else:
            return redirect(url_for('managerlog'))

    return render_template('managerlog.html')

@app.route('/manager/<int:employee_id>')
@app.route('/manager/<int:employee_id>/Mprofile') 
def manager(employee_id, Mprofile=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get basic employee info with manager details
    cursor.execute("""
        SELECT e.*, m.employee_name as manager_name, m.email_address as manager_email
        FROM Employee e
        LEFT JOIN Employee m ON e.manager_id = m.employee_id
        WHERE e.employee_id = %s
    """, (employee_id,))
    employee = cursor.fetchone()
    
    if not employee:
        conn.close()
        return "Employee not found", 404
    
    # Only fetch detailed employment data if we're viewing the Mprofile
    hourly_data = None
    contract_data = None
    
    if request.path.endswith('/Mprofile') or request.args.get('Mprofile'):
        cursor.execute("SELECT * FROM HourlyEmployee WHERE employee_id = %s", (employee_id,))
        hourly_data = cursor.fetchone()
        
        cursor.execute("SELECT * FROM ContractEmployee WHERE employee_id = %s", (employee_id,))
        contract_data = cursor.fetchone()
    
    conn.close()
    
    # Determine which template to render
    if request.path.endswith('/Mprofile') or request.args.get('Mprofile'):
        return render_template('manager.html', 
                            employee=employee,
                            hourly_data=hourly_data,
                            contract_data=contract_data,
                            show_profile=True)
    else:
        return render_template('manager.html', employee=employee)

@app.route('/m_customers/')
def m_customers():
    """Render the customers management page"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee", )
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('emplog'))
    
    return render_template('m_customers.html', employee=employee)

@app.route('/api/manager/customers')
def get_all_customers():
    """Get all customers with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        base_query = '''
            SELECT 
                customer_id, 
                customer_name, 
                email_address, 
                phone_number,
                city,
                order_count,
                is_valid
            FROM customer
            WHERE is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'customer_id':
                conditions.append("customer_id = %s")
                params.append(int(search_value))
            elif search_by == 'customer_name':
                conditions.append("customer_name LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'email_address':
                conditions.append("email_address LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'phone_number':
                conditions.append("phone_number LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'city':
                conditions.append("city LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'is_valid':
                # Convert to boolean (1 for true/active, 0 for false/inactive)
                is_valid = 1 if search_value.lower() in ['true', '1', 'active'] else 0
                conditions.append("is_valid = %s")
                params.append(is_valid)
        
        # Build final query
        query = base_query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY customer_id ASC"
        
        cursor.execute(query, params)
        customers = cursor.fetchall()
        conn.close()
        
        customers_list = []
        for customer in customers:
            customers_list.append({
                'customer_id': customer['customer_id'],
                'customer_name': customer['customer_name'],
                'email_address': customer['email_address'],
                'phone_number': customer['phone_number'],
                'city': customer['city'],
                'order_count': customer['order_count'],
                'is_valid': bool(customer['is_valid'])
            })
        
        return jsonify(customers_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/customers/<int:customer_id>', methods=['DELETE'])
def deactivate_customer(customer_id):
    """Delete a customer by setting is_valid to FALSE"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Soft delete by setting is_valid to FALSE
        cursor.execute("""
            UPDATE customer 
            SET is_valid = FALSE 
            WHERE customer_id = %s
        """, (customer_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Customer deleted successfully',
            'customer_id': customer_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/m_employees/')
def m_employees():
    """Render the employees management page"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get list of all managers for dropdown
    cursor.execute("""
        SELECT employee_id, employee_name 
        FROM employee 
        WHERE is_valid = TRUE AND emp_role LIKE '%Manager%'
        ORDER BY employee_name
    """)
    managers = cursor.fetchall()
    
    conn.close()
    
    return render_template('m_employees.html', managers=managers, now=datetime.now)

@app.route('/api/manager/employees', methods=['POST'])
def create_employee():
    """Create a new employee with optional hourly/contract details"""
    conn = None
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['employee_name', 'emp_role', 'email_address', 'hire_date', 'employee_type']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email_address']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone number if provided
        if 'phone_number' in data and data['phone_number'] and not re.match(r'^\d{10}$', data['phone_number']):
            return jsonify({'error': 'Phone number must be 10 digits'}), 400
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Generate password (employeeID + 'pass')
        # We'll update this after we know the employee ID
        temp_password = 'temp_password'
        
        # Insert into employee table
        cursor.execute("""
            INSERT INTO employee (
                employee_name, 
                emp_role, 
                phone_number, 
                email_address, 
                hire_date, 
                manager_id, 
                password, 
                is_valid
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['employee_name'],
            data['emp_role'],
            data.get('phone_number'),
            data['email_address'],
            data['hire_date'],
            data.get('manager_id'),
            temp_password,
            1  # is_valid
        ))
        
        employee_id = cursor.lastrowid
        
        # Now set the actual password
        actual_password = f"{employee_id}pass"
        cursor.execute("""
            UPDATE employee 
            SET password = %s 
            WHERE employee_id = %s
        """, (actual_password, employee_id))
        
        # Handle employee type specific tables
        if data['employee_type'].lower() == 'hourly':
            if 'hours_worked' not in data or 'hourly_wages' not in data:
                conn.rollback()
                return jsonify({'error': 'Missing required fields for hourly employee'}), 400
                
            if float(data['hours_worked']) < 0 or float(data['hourly_wages']) <= 0:
                conn.rollback()
                return jsonify({'error': 'Hours worked must be >= 0 and hourly wage must be > 0'}), 400
                
            cursor.execute("""
                INSERT INTO hourlyemployee (
                    employee_id, 
                    hours_worked, 
                    hourly_wages, 
                    is_valid
                ) VALUES (%s, %s, %s, %s)
            """, (
                employee_id,
                data['hours_worked'],
                data['hourly_wages'],
                1
            ))
            
        elif data['employee_type'].lower() == 'contract':
            required_contract_fields = ['contract_id', 'contract_start_date', 'contract_end_date', 'salary']
            for field in required_contract_fields:
                if field not in data or not data[field]:
                    conn.rollback()
                    return jsonify({'error': f'Missing required field for contract employee: {field}'}), 400
            
            # Validate contract dates
            start_date = datetime.strptime(data['contract_start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(data['contract_end_date'], '%Y-%m-%d')
            if start_date >= end_date:
                conn.rollback()
                return jsonify({'error': 'Contract end date must be after start date'}), 400
                
            if float(data['salary']) <= 0:
                conn.rollback()
                return jsonify({'error': 'Salary must be positive'}), 400
                
            # First insert into contract table
            cursor.execute("""
                INSERT INTO contract (
                    contract_id,
                    contract_start_date, 
                    contract_end_date, 
                    salary, 
                    is_valid
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                data['contract_id'],
                data['contract_start_date'],
                data['contract_end_date'],
                data['salary'],
                1
            ))
            
            # Then insert into contractemployee table
            cursor.execute("""
                INSERT INTO contractemployee (
                    employee_id, 
                    contract_id, 
                    is_valid
                ) VALUES (%s, %s, %s)
            """, (
                employee_id,
                data['contract_id'],
                1
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Employee created successfully',
            'employee_id': employee_id,
            'password': actual_password
        }), 201
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/employees')
def get_all_employees():
    """Get all employees with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        base_query = '''
            SELECT 
                e.employee_id, 
                e.employee_name, 
                e.emp_role, 
                e.email_address, 
                e.phone_number,
                e.hire_date,
                e.is_valid,
                CASE 
                    WHEN he.employee_id IS NOT NULL THEN 'Hourly'
                    WHEN ce.employee_id IS NOT NULL THEN 'Contract'
                    ELSE 'Regular'
                END AS employee_type
            FROM employee e
            LEFT JOIN hourlyemployee he ON e.employee_id = he.employee_id AND he.is_valid = TRUE
            LEFT JOIN contractemployee ce ON e.employee_id = ce.employee_id AND ce.is_valid = TRUE
            WHERE e.is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'employee_id':
                conditions.append("e.employee_id = %s")
                params.append(int(search_value))
            elif search_by == 'employee_name':
                conditions.append("e.employee_name LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'emp_role':
                conditions.append("e.emp_role LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'email_address':
                conditions.append("e.email_address LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'phone_number':
                conditions.append("e.phone_number LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'employee_type':
                if search_value.lower() == 'hourly':
                    conditions.append("he.employee_id IS NOT NULL")
                elif search_value.lower() == 'contract':
                    conditions.append("ce.employee_id IS NOT NULL")
                else:
                    conditions.append("he.employee_id IS NULL AND ce.employee_id IS NULL")
            elif search_by == 'is_valid':
                # Convert to boolean (1 for true/active, 0 for false/inactive)
                is_valid = 1 if search_value.lower() in ['true', '1', 'active'] else 0
                conditions.append("e.is_valid = %s")
                params.append(is_valid)
        
        # Build final query
        query = base_query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY e.employee_id ASC"
        
        cursor.execute(query, params)
        employees = cursor.fetchall()
        conn.close()
        
        employees_list = []
        for employee in employees:
            employees_list.append({
                'employee_id': employee['employee_id'],
                'employee_name': employee['employee_name'],
                'emp_role': employee['emp_role'],
                'email_address': employee['email_address'],
                'phone_number': employee['phone_number'],
                'hire_date': employee['hire_date'].strftime('%Y-%m-%d') if employee['hire_date'] else None,
                'employee_type': employee['employee_type'],
                'is_valid': bool(employee['is_valid'])
            })
        
        return jsonify(employees_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/employees/<int:employee_id>', methods=['DELETE'])
def deactivate_employee(employee_id):
    """Delete an employee by setting is_valid to FALSE in all related tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Check if employee exists
        cursor.execute("SELECT employee_id FROM employee WHERE employee_id = %s AND is_valid = TRUE", (employee_id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Employee not found or already inactive'}), 404
        
        # Soft delete from hourlyemployee if exists
        cursor.execute("""
            UPDATE hourlyemployee 
            SET is_valid = FALSE 
            WHERE employee_id = %s AND is_valid = TRUE
        """, (employee_id,))
        
        # Soft delete from contractemployee if exists
        cursor.execute("""
            UPDATE contractemployee 
            SET is_valid = FALSE 
            WHERE employee_id = %s AND is_valid = TRUE
        """, (employee_id,))
        
        # Soft delete from employee
        cursor.execute("""
            UPDATE employee 
            SET is_valid = FALSE 
            WHERE employee_id = %s
        """, (employee_id,))
        
        if cursor.rowcount == 0:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Employee not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Employee deleted successfully',
            'employee_id': employee_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/employees/<int:employee_id>')
def get_employee(employee_id):
    """Get a single employee with all details"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get basic employee info
        cursor.execute("""
            SELECT 
                e.*,
                CASE 
                    WHEN he.employee_id IS NOT NULL THEN 'Hourly'
                    WHEN ce.employee_id IS NOT NULL THEN 'Contract'
                    ELSE 'Regular'
                END AS employee_type
            FROM employee e
            LEFT JOIN hourlyemployee he ON e.employee_id = he.employee_id AND he.is_valid = TRUE
            LEFT JOIN contractemployee ce ON e.employee_id = ce.employee_id AND ce.is_valid = TRUE
            WHERE e.employee_id = %s AND e.is_valid = TRUE
        """, (employee_id,))
        
        employee = cursor.fetchone()
        
        if not employee:
            conn.close()
            return jsonify({'error': 'Employee not found'}), 404
        
        # Get additional details based on type
        if employee['employee_type'] == 'Hourly':
            cursor.execute("""
                SELECT hours_worked, hourly_wages 
                FROM hourlyemployee 
                WHERE employee_id = %s AND is_valid = TRUE
            """, (employee_id,))
            hourly_data = cursor.fetchone()
            if hourly_data:
                employee.update(hourly_data)
                
        elif employee['employee_type'] == 'Contract':
            cursor.execute("""
                SELECT c.contract_start_date, c.contract_end_date, c.salary
                FROM contractemployee ce
                JOIN contract c ON ce.contract_id = c.contract_id
                WHERE ce.employee_id = %s AND ce.is_valid = TRUE AND c.is_valid = TRUE
            """, (employee_id,))
            contract_data = cursor.fetchone()
            if contract_data:
                employee.update(contract_data)
        
        conn.close()
        
        # Format dates for JSON
        if 'hire_date' in employee and employee['hire_date']:
            employee['hire_date'] = employee['hire_date'].strftime('%Y-%m-%d')
        if 'contract_start_date' in employee and employee['contract_start_date']:
            employee['contract_start_date'] = employee['contract_start_date'].strftime('%Y-%m-%d')
        if 'contract_end_date' in employee and employee['contract_end_date']:
            employee['contract_end_date'] = employee['contract_end_date'].strftime('%Y-%m-%d')
        
        return jsonify(employee)
    
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/manager/employees/<int:employee_id>', methods=['PUT'])
def update_employee(employee_id):
    """Update an existing employee"""
    try:
        data = request.get_json()
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # First check if employee exists
        cursor.execute("SELECT * FROM employee WHERE employee_id = %s AND is_valid = TRUE", (employee_id,))
        employee = cursor.fetchone()
        
        if not employee:
            conn.close()
            return jsonify({'error': 'Employee not found'}), 404
        
        # Update employee table
        cursor.execute("""
            UPDATE employee 
            SET 
                employee_name = %s,
                emp_role = %s,
                phone_number = %s,
                email_address = %s,
                hire_date = %s,
                manager_id = %s
            WHERE employee_id = %s
        """, (
            data.get('employee_name', employee['employee_name']),
            data.get('emp_role', employee['emp_role']),
            data.get('phone_number', employee['phone_number']),
            data.get('email_address', employee['email_address']),
            data.get('hire_date', employee['hire_date']),
            data.get('manager_id', employee['manager_id']),
            employee_id
        ))
        
        # Handle employee type changes if needed
        if 'employee_type' in data:
            # First remove from any existing type tables
            cursor.execute("""
                UPDATE hourlyemployee 
                SET is_valid = FALSE 
                WHERE employee_id = %s AND is_valid = TRUE
            """, (employee_id,))
            
            cursor.execute("""
                UPDATE contractemployee 
                SET is_valid = FALSE 
                WHERE employee_id = %s AND is_valid = TRUE
            """, (employee_id,))
            
            # Then add to new type table if specified
            if data['employee_type'].lower() == 'hourly':
                if 'hours_worked' not in data or 'hourly_wages' not in data:
                    conn.rollback()
                    return jsonify({'error': 'Missing required fields for hourly employee'}), 400
                    
                cursor.execute("""
                    INSERT INTO hourlyemployee (
                        employee_id, 
                        hours_worked, 
                        hourly_wages, 
                        is_valid
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    employee_id,
                    data['hours_worked'],
                    data['hourly_wages'],
                    1
                ))
                
            elif data['employee_type'].lower() == 'contract':
                if 'contract_start_date' not in data or 'contract_end_date' not in data or 'salary' not in data:
                    conn.rollback()
                    return jsonify({'error': 'Missing required fields for contract employee'}), 400
                    
                # Insert into contract table
                cursor.execute("""
                    INSERT INTO contract (
                        contract_start_date, 
                        contract_end_date, 
                        salary, 
                        is_valid
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    data['contract_start_date'],
                    data['contract_end_date'],
                    data['salary'],
                    1
                ))
                
                contract_id = cursor.lastrowid
                
                # Insert into contractemployee table
                cursor.execute("""
                    INSERT INTO contractemployee (
                        employee_id, 
                        contract_id, 
                        is_valid
                    ) VALUES (%s, %s, %s)
                """, (
                    employee_id,
                    contract_id,
                    1
                ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Employee updated successfully',
            'employee_id': employee_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/m_suppliers/')
def m_suppliers():
    """Render the suppliers management page"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee", )
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('emplog'))
    
    return render_template('m_suppliers.html', employee=employee)

@app.route('/api/manager/suppliers')
def get_all_suppliers():
    """Get all suppliers with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        base_query = '''
            SELECT 
                supplier_id, 
                supplier_name, 
                email_address, 
                phone_number,
                is_valid
            FROM supplier
            WHERE is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'supplier_id':
                conditions.append("supplier_id = %s")
                params.append(int(search_value))
            elif search_by == 'supplier_name':
                conditions.append("supplier_name LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'email_address':
                conditions.append("email_address LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'phone_number':
                conditions.append("phone_number LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'is_valid':
                # Convert to boolean (1 for true/active, 0 for false/inactive)
                is_valid = 1 if search_value.lower() in ['true', '1', 'active'] else 0
                conditions.append("is_valid = %s")
                params.append(is_valid)
        
        # Build final query
        query = base_query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY supplier_id ASC"
        
        cursor.execute(query, params)
        suppliers = cursor.fetchall()
        conn.close()
        
        suppliers_list = []
        for supplier in suppliers:
            suppliers_list.append({
                'supplier_id': supplier['supplier_id'],
                'supplier_name': supplier['supplier_name'],
                'email_address': supplier['email_address'],
                'phone_number': supplier['phone_number'],
                'is_valid': bool(supplier['is_valid'])
            })
        
        return jsonify(suppliers_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/suppliers/<int:supplier_id>', methods=['DELETE'])
def deactivate_supplier(supplier_id):
    """Delete a supplier by setting is_valid to FALSE"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Soft delete by setting is_valid to FALSE
        cursor.execute("""
            UPDATE supplier 
            SET is_valid = FALSE 
            WHERE supplier_id = %s
        """, (supplier_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Supplier not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Supplier deleted successfully',
            'supplier_id': supplier_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

# Optional additional endpoints for full CRUD functionality
@app.route('/api/manager/suppliers', methods=['POST'])
def create_supplier():
    """Create a new supplier"""
    try:
        data = request.get_json()
        required_fields = ['supplier_name']
        
        # Validate required fields
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            INSERT INTO supplier (supplier_name, email_address, phone_number, is_valid)
            VALUES (%s, %s, %s, %s)
        """, (
            data['supplier_name'],
            data.get('email_address'),
            data.get('phone_number'),
            data.get('is_valid', True)
        ))
        
        supplier_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Supplier created successfully',
            'supplier_id': supplier_id
        }), 201
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/suppliers/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    """Update an existing supplier"""
    try:
        data = request.get_json()
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First get current supplier data
        cursor.execute("""
            SELECT * FROM supplier 
            WHERE supplier_id = %s AND is_valid = TRUE
        """, (supplier_id,))
        supplier = cursor.fetchone()
        
        if not supplier:
            conn.close()
            return jsonify({'error': 'Supplier not found'}), 404
        
        # Update only the fields that were provided
        update_fields = []
        params = []
        
        if 'supplier_name' in data:
            update_fields.append("supplier_name = %s")
            params.append(data['supplier_name'])
        
        if 'email_address' in data:
            update_fields.append("email_address = %s")
            params.append(data['email_address'])
        
        if 'phone_number' in data:
            update_fields.append("phone_number = %s")
            params.append(data['phone_number'])
        
        if 'is_valid' in data:
            update_fields.append("is_valid = %s")
            params.append(data['is_valid'])
        
        if not update_fields:
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Build and execute update query
        update_query = "UPDATE supplier SET " + ", ".join(update_fields) + " WHERE supplier_id = %s"
        params.append(supplier_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Supplier updated successfully',
            'supplier_id': supplier_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500 

@app.route('/m_orders/')
def m_orders():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee", )
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('emplog'))
    
    return render_template('m_orders.html', employee=employee)

@app.route('/api/manager/Morders')
def get_all_orders():
    """Get all orders with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        base_query = '''
            SELECT 
                o.order_id, 
                o.customer_id, 
                o.employee_id, 
                o.order_date, 
                o.expected_received_date, 
                o.actual_received_date,
                COALESCE(SUM(od.price * od.quantity), 0) AS total_price
            FROM `Order` o
            LEFT JOIN OrderDetails od ON o.order_id = od.order_id AND od.is_valid = TRUE
            WHERE o.is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'order_id':
                conditions.append("o.order_id = %s")
                params.append(int(search_value))
            elif search_by == 'customer_id':
                conditions.append("o.customer_id = %s")
                params.append(int(search_value))
            elif search_by == 'total_price':
                conditions.append("COALESCE(SUM(od.price * od.quantity), 0) = %s")
                params.append(float(search_value))
            elif search_by == 'status':
                if search_value == 'pending':
                    conditions.append("o.actual_received_date IS NULL")
                elif search_value == 'completed':
                    conditions.append("o.actual_received_date IS NOT NULL AND o.actual_received_date <= o.expected_received_date")
                elif search_value == 'delayed':
                    conditions.append("o.actual_received_date IS NOT NULL AND o.actual_received_date > o.expected_received_date")
        
        # Build final query
        query = base_query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " GROUP BY o.order_id, o.customer_id, o.employee_id, o.order_date, o.expected_received_date, o.actual_received_date"
        query += " ORDER BY o.order_id ASC"
        
        cursor.execute(query, params)
        orders = cursor.fetchall()
        conn.close()
        
        orders_list = []
        for order in orders:
            orders_list.append({
                'order_id': order['order_id'],
                'customer_id': order['customer_id'],
                'employee_id': order['employee_id'],
                'order_date': str(order['order_date']),
                'expected_received_date': str(order['expected_received_date']),
                'actual_received_date': str(order['actual_received_date']) if order['actual_received_date'] else None,
                'total_price': float(order['total_price'])
            })
        
        return jsonify(orders_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@app.route('/m_p_orders/<int:employee_id>')
def m_p_orders(employee_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('emplog'))
    
    return render_template('m_p_orders.html', employee=employee)

# Add these routes to your app.py file

@app.route('/m_products/')
def m_products():
    """Render the products management page"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee")
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('mangerlog'))
    
    return render_template('m_products.html', employee=employee)

@app.route('/api/manager/products')
def get_all_products():
    """Get all products with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        base_query = '''
            SELECT 
                product_id, 
                product_name, 
                category,
                price,
                stock_quantity,
                stock_arrival_date,
                is_valid
            FROM Product
            WHERE is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'product_id':
                conditions.append("product_id = %s")
                params.append(int(search_value))
            elif search_by == 'product_name':
                conditions.append("product_name LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'category':
                conditions.append("category LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'price':
                conditions.append("price = %s")
                params.append(float(search_value))
            elif search_by == 'is_valid':
                # Convert to boolean (1 for true/active, 0 for false/inactive)
                is_valid = 1 if search_value.lower() in ['true', '1', 'active'] else 0
                conditions.append("is_valid = %s")
                params.append(is_valid)
        
        # Build final query
        query = base_query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY product_id ASC"
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        conn.close()
        
        products_list = []
        for product in products:
            products_list.append({
                'product_id': product['product_id'],
                'product_name': product['product_name'],
                'category': product['category'],
                'price': float(product['price']),
                'stock_quantity': product['stock_quantity'],
                'stock_arrival_date': product['stock_arrival_date'].strftime('%Y-%m-%d') if product['stock_arrival_date'] else None,
                'is_valid': bool(product['is_valid'])
            })
        
        return jsonify(products_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/products/<int:product_id>', methods=['DELETE'])
def deactivate_product(product_id):
    """Deactivate a product by setting is_valid to FALSE"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Soft delete by setting is_valid to FALSE
        cursor.execute("""
            UPDATE Product 
            SET is_valid = FALSE 
            WHERE product_id = %s
        """, (product_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product deactivated successfully',
            'product_id': product_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/products', methods=['POST'])
def create_product():
    """Create a new product"""
    try:
        data = request.get_json()
        required_fields = ['product_name', 'category', 'price', 'stock_quantity', 'stock_arrival_date']
        
        # Validate required fields
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate price is positive
        if float(data['price']) <= 0:
            return jsonify({'error': 'Price must be positive'}), 400
        
        # Validate stock quantity is non-negative
        if int(data['stock_quantity']) < 0:
            return jsonify({'error': 'Stock quantity cannot be negative'}), 400
        
        # Validate stock arrival date is in the future
        stock_arrival_date = datetime.strptime(data['stock_arrival_date'], '%Y-%m-%d').date()
        today = date.today()
        if stock_arrival_date <= today:
            return jsonify({'error': 'Stock arrival date must be in the future (not today or earlier)'}), 400
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            INSERT INTO Product (
                product_name, 
                category, 
                price, 
                stock_quantity, 
                stock_arrival_date,
                is_valid
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data['product_name'],
            data['category'],
            float(data['price']),
            int(data['stock_quantity']),
            stock_arrival_date,
            1  # is_valid
        ))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product created successfully',
            'product_id': product_id
        }), 201
    
    except ValueError as e:
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update an existing product"""
    try:
        data = request.get_json()
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First get current product data
        cursor.execute("""
            SELECT * FROM Product 
            WHERE product_id = %s AND is_valid = TRUE
        """, (product_id,))
        product = cursor.fetchone()
        
        if not product:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        # Validate stock arrival date if provided
        if 'stock_arrival_date' in data and data['stock_arrival_date']:
            stock_arrival_date = datetime.strptime(data['stock_arrival_date'], '%Y-%m-%d').date()
            today = date.today()
            if stock_arrival_date <= today:
                conn.close()
                return jsonify({'error': 'Stock arrival date must be in the future (not today or earlier)'}), 400
        
        # Update only the fields that were provided
        update_fields = []
        params = []
        
        if 'product_name' in data:
            update_fields.append("product_name = %s")
            params.append(data['product_name'])
        
        if 'category' in data:
            update_fields.append("category = %s")
            params.append(data['category'])
        
        if 'price' in data:
            if float(data['price']) <= 0:
                conn.close()
                return jsonify({'error': 'Price must be positive'}), 400
            update_fields.append("price = %s")
            params.append(float(data['price']))
        
        if 'stock_quantity' in data:
            if int(data['stock_quantity']) < 0:
                conn.close()
                return jsonify({'error': 'Stock quantity cannot be negative'}), 400
            update_fields.append("stock_quantity = %s")
            params.append(int(data['stock_quantity']))
        
        if 'stock_arrival_date' in data and data['stock_arrival_date']:
            update_fields.append("stock_arrival_date = %s")
            params.append(datetime.strptime(data['stock_arrival_date'], '%Y-%m-%d').date())
        
        if 'is_valid' in data:
            update_fields.append("is_valid = %s")
            params.append(1 if data['is_valid'] else 0)
        
        if not update_fields:
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Build and execute update query
        update_query = "UPDATE Product SET " + ", ".join(update_fields) + " WHERE product_id = %s"
        params.append(product_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product updated successfully',
            'product_id': product_id
        })
    
    except ValueError as e:
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500   

@app.route('/emplog', methods=['GET', 'POST'])
def emplog():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        password = request.form['password']
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM Employee WHERE employee_id = %s"
        cursor.execute(query, (employee_id,))
        emp = cursor.fetchone()
        cursor.close()
        conn.close()

        if emp:
            if password == '1234':  
                return redirect(url_for('emp', employee_id=employee_id))
            else:
                print("Wrong password")
                return redirect(url_for('emplog'))
        else:
            print("No such employee")
            return redirect(url_for('emplog'))

    return render_template('emplog.html')

@app.route('/emp/<int:employee_id>')
@app.route('/emp/<int:employee_id>/profile') 
def emp(employee_id, profile=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get basic employee info with manager details
    cursor.execute("""
        SELECT e.*, m.employee_name as manager_name, m.email_address as manager_email
        FROM Employee e
        LEFT JOIN Employee m ON e.manager_id = m.employee_id
        WHERE e.employee_id = %s
    """, (employee_id,))
    employee = cursor.fetchone()
    
    if not employee:
        conn.close()
        return "Employee not found", 404
    
    # Only fetch detailed employment data if we're viewing the profile
    hourly_data = None
    contract_data = None
    
    if request.path.endswith('/profile') or request.args.get('profile'):
        cursor.execute("SELECT * FROM HourlyEmployee WHERE employee_id = %s", (employee_id,))
        hourly_data = cursor.fetchone()
        
        cursor.execute("SELECT * FROM ContractEmployee WHERE employee_id = %s", (employee_id,))
        contract_data = cursor.fetchone()
    
    conn.close()
    
    # Determine which template to render
    if request.path.endswith('/profile') or request.args.get('profile'):
        return render_template('emp.html', 
                            employee=employee,
                            hourly_data=hourly_data,
                            contract_data=contract_data,
                            show_profile=True)
    else:
        return render_template('emp.html', employee=employee)
     
@app.route('/e_orders/<int:employee_id>')
def e_orders(employee_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('emplog'))
    
    return render_template('e_orders.html', employee=employee)

@app.route('/api/employees/<int:employee_id>/orders')
def get_employee_orders(employee_id):
    """Get all orders for a specific employee"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT order_id, customer_id, employee_id, 
                   order_date, expected_received_date, actual_received_date
            FROM `Order`
            WHERE employee_id = %s
            ORDER BY order_id ASC
        ''', (employee_id,))
        
        orders = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        orders_list = []
        for order in orders:
            orders_list.append({
                'order_id': order['order_id'],
                'customer_id': order['customer_id'],
                'employee_id': order['employee_id'],
                'order_date': str(order['order_date']),
                'expected_received_date': str(order['expected_received_date']),
                'actual_received_date': str(order['actual_received_date']) if order['actual_received_date'] else None
            })
        
        return jsonify(orders_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees/<int:employee_id>/orders/search', methods=['POST'])
def search_employee_orders(employee_id):
    """Search orders for a specific employee"""
    try:
        data = request.get_json()
        attribute = data.get('attribute')
        value = data.get('value')
        
        if not attribute or not value:
            return jsonify({'error': 'Missing search parameters'}), 400
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query for this employee's orders
        query = '''
            SELECT order_id, customer_id, employee_id, 
                   order_date, expected_received_date, actual_received_date
            FROM `Order`
            WHERE employee_id = %s
        '''
        params = [employee_id]
        
        # Add search conditions based on attribute
        if attribute == 'order_id':
            query += ' AND order_id = %s'
            params.append(int(value))
        elif attribute == 'customer_id':
            query += ' AND customer_id = %s'
            params.append(int(value))
            params.append(float(value))
        elif attribute == 'order_date':
            query += ' AND DATE(order_date) = %s'
            params.append(value)
        else:
            return jsonify({'error': 'Invalid search attribute'}), 400
        
        query += ' ORDER BY order_id ASC'
        
        cursor.execute(query, tuple(params))
        orders = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        orders_list = []
        for order in orders:
            orders_list.append({
                'order_id': order['order_id'],
                'customer_id': order['customer_id'],
                'employee_id': order['employee_id'],
                'order_date': str(order['order_date']),
                'expected_received_date': str(order['expected_received_date']),
                'actual_received_date': str(order['actual_received_date']) if order['actual_received_date'] else None
            })
        
        return jsonify({'orders': orders_list})
    
    except ValueError as e:
        return jsonify({'error': 'Invalid value type for search'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/e_purchase-orders/<int:employee_id>')
def e_purchase_orders(employee_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('emplog'))
    
    return render_template('e_purchase_orders.html', employee_id=employee_id)

@app.route('/e_products/<int:employee_id>')
def e_products(employee_id):
    """Products management page for employees"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get employee info
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    
    if not employee:
        conn.close()
        return redirect(url_for('emplog'))
    
    # Get products data
    cursor.execute('''
        SELECT product_id, product_name, category,
                   price, stock_quantity, stock_arrival_date
            FROM Product
            ORDER BY product_id
    ''')
    products = cursor.fetchall()
    conn.close()
    
    return render_template('e_products.html', employee=employee, products=products)

@app.route('/e_invoices/<int:employee_id>')
def e_invoices(employee_id):
    """Invoices management page for employees"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    
    if not employee:
        conn.close()
        return redirect(url_for('emplog'))
    
    # Get invoices data
    cursor.execute('''
        SELECT invoice_id, order_id, invoice_date, due_date, status, payment_method
        FROM Invoice
        WHERE employee_id = %s
        ORDER BY invoice_date ASC
    ''', (employee_id,))
    
    invoices = cursor.fetchall()
    conn.close()
    
    return render_template('e_invoices.html', employee=employee, invoices=invoices)

@app.route('/api/employees/<int:employee_id>/invoices')
def get_employee_invoices(employee_id):
    """API endpoint for employee invoices data"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT invoice_id, order_id, invoice_date, due_date,
                   status, payment_method
            FROM Invoice
            WHERE employee_id = %s
            ORDER BY invoice_date ASC
        ''', (employee_id,))
        
        invoices = cursor.fetchall()
        conn.close()
        
        invoices_list = []
        for invoice in invoices:
            invoices_list.append({
                'invoice_id': invoice['invoice_id'],
                'order_id': invoice['order_id'],
                'invoice_date': str(invoice['invoice_date']),
                'due_date': str(invoice['due_date']),
                'status': invoice['status'],
                'payment_method': invoice['payment_method']
            })
        
        return jsonify(invoices_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/e_reports/<int:employee_id>')
def e_reports(employee_id):
    """Reports page for employees"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    
    if not employee:
        conn.close()
        return redirect(url_for('emplog'))
    
    # Get available report types (could be from database or hardcoded)
    cursor.execute('''
        SELECT report_id, report_name, ASCription, last_generated
        FROM AvailableReports
        WHERE employee_accessible = TRUE
    ''')
    reports = cursor.fetchall()
    conn.close()
    
    # If no reports table exists, use default reports
    if not reports:
        reports = [
            {'report_id': 1, 'report_name': 'Sales Summary', 'ASCription': 'Monthly sales figures'},
            {'report_id': 2, 'report_name': 'Inventory Levels', 'ASCription': 'Current stock status'},
            {'report_id': 3, 'report_name': 'Customer Orders', 'ASCription': 'Recent customer orders'}
        ]
    
    return render_template('e_reports.html', employee=employee, reports=reports)

@app.route('/api/employees/<int:employee_id>/reports')
def get_employee_reports(employee_id):
    """API endpoint for employee reports data"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First verify employee exists
        cursor.execute("SELECT 1 FROM Employee WHERE employee_id = %s", (employee_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Employee not found'}), 404
        
        # Get report metadata
        cursor.execute('''
            SELECT report_id, report_name, ASCription, last_generated
            FROM AvailableReports
            WHERE employee_accessible = TRUE
        ''')
        
        reports = cursor.fetchall()
        conn.close()
        
        # Format response
        reports_list = []
        for report in reports:
            reports_list.append({
                'report_id': report['report_id'],
                'report_name': report['report_name'],
                'ASCription': report['ASCription'],
                'last_generated': str(report['last_generated']) if report.get('last_generated') else None
            })
        
        return jsonify(reports_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/m_report')
def m_report():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total_employees FROM Employee WHERE is_valid = TRUE")
    total_employees = cursor.fetchone()['total_employees']

    cursor.execute("SELECT COUNT(*) AS total_customers FROM Customer WHERE is_valid = TRUE")
    total_customers = cursor.fetchone()['total_customers']

    cursor.execute("SELECT COUNT(*) AS total_suppliers FROM Supplier WHERE is_valid = TRUE")
    total_suppliers = cursor.fetchone()['total_suppliers']

    cursor.execute("SELECT COUNT(*) AS total_orders FROM `Order` WHERE is_valid = TRUE")
    total_orders = cursor.fetchone()['total_orders']

    cursor.execute("SELECT COUNT(*) AS total_purchase_orders FROM PurchaseOrder WHERE is_valid = TRUE")
    total_purchase_orders = cursor.fetchone()['total_purchase_orders']

    cursor.execute("SELECT COUNT(*) AS total_products FROM Product WHERE is_valid = TRUE")
    total_products = cursor.fetchone()['total_products']

    cursor.execute("SELECT COUNT(*) AS pending_deliveries FROM PurchaseOrder WHERE delivery_status = 'Pending' AND is_valid = TRUE")
    pending_deliveries = cursor.fetchone()['pending_deliveries']

    cursor.execute("SELECT SUM(amount_paid) AS total_revenue FROM Payment WHERE is_valid = TRUE")
    total_revenue = cursor.fetchone()['total_revenue']


    # Employees under each manager
    cursor.execute("""
    SELECT 
        m.employee_name AS manager_name,
        e.employee_name AS employee_name,
        e.emp_role,
        DATE_FORMAT(e.hire_date, '%%Y-%%m-%%d') AS hire_date
    FROM Employee e
    JOIN Employee m ON m.employee_id = e.manager_id
    WHERE e.is_valid = TRUE
    AND e.manager_id IN (
        SELECT manager_id
        FROM Employee
        WHERE is_valid = TRUE
        GROUP BY manager_id
        HAVING COUNT(*) > 2
    )
    ORDER BY m.employee_name, e.employee_name
    """)
    employees_by_manager = cursor.fetchall()

    # Purchase orders
    cursor.execute("""
        SELECT s.supplier_name, p.purchase_order_id, p.order_date, p.delivery_status
        FROM PurchaseOrder p
        JOIN Supplier s ON p.supplier_id = s.supplier_id
        WHERE p.is_valid = TRUE
        ORDER BY p.order_date DESC
        LIMIT 10
    """)
    purchase_orders = cursor.fetchall()

    # Salary summary
    cursor.execute("""
        SELECT e.employee_name, 'Hourly' AS type, 
               CONCAT('$', he.hourly_wages) AS salary_or_wage,
               CONCAT('$', (he.hours_worked * he.hourly_wages)) AS total_pay
        FROM HourlyEmployee he
        JOIN Employee e ON he.employee_id = e.employee_id
        WHERE he.is_valid = TRUE

        UNION

        SELECT e.employee_name, 'Contract' AS type, 
               CONCAT('$', c.salary) AS salary_or_wage,
               NULL AS total_pay
        FROM ContractEmployee ce
        JOIN Contract c ON ce.contract_id = c.contract_id
        JOIN Employee e ON ce.employee_id = e.employee_id
        WHERE ce.is_valid = TRUE AND c.is_valid = TRUE
    """)
    salary_data = cursor.fetchall()

    # Sidebar display info
    cursor.execute("SELECT * FROM Employee WHERE emp_role LIKE '%Manager%' LIMIT 1")
    employee = cursor.fetchone()

    #----------
    cursor.execute("""
    SELECT c.customer_id, c.customer_name, SUM(od.price * od.quantity) AS total_spent
    FROM Customer c, `Order` o,OrderDetails od 
    WHERE c.customer_id = o.customer_id AND o.order_id = od.order_id
    GROUP BY c.customer_id, c.customer_name
    ORDER BY total_spent DESC
    LIMIT 4;
    """)
    customer_q1 = cursor.fetchall()

    conn.close()

    return render_template("m_report.html",
        employee=employee,
        total_employees=total_employees,
        total_customers=total_customers,
        total_suppliers=total_suppliers,
        total_orders=total_orders,
        total_purchase_orders=total_purchase_orders,
        total_products=total_products,
        total_revenue = total_revenue,
        pending_deliveries=pending_deliveries,
        employees_by_manager=employees_by_manager,
        customer_q1=customer_q1,
        purchase_orders=purchase_orders,
        salary_data=salary_data
    )

if __name__ == '__main__':
    app.run(debug=True)
