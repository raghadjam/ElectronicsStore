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
        cursor.execute("SELECT * FROM Customer WHERE customer_id = %s AND Customer_password = %s AND is_valid = TRUE", (customer_id, password))
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
    if 'customer_id' not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('customerlogin'))

    customer_id = session['customer_id']
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Customer basic info
    cursor.execute("SELECT * FROM Customer WHERE customer_id = %s", (customer_id,))
    customer = cursor.fetchone()

    if not customer:
        session.pop('customer_id', None)
        flash("User not found. Please log in again.", "error")
        return redirect(url_for('customerlogin'))

    # 2. Total orders made by the customer
    cursor.execute("SELECT COUNT(*) FROM `Order` WHERE customer_id = %s AND is_valid = TRUE", (customer_id,))
    user_order_count = cursor.fetchone()[0]

    # 3. Total amount spent by the customer
    cursor.execute("""
        SELECT SUM(od.price * od.quantity)
        FROM `Order` o
        JOIN OrderDetails od ON o.order_id = od.order_id
        WHERE o.customer_id = %s AND o.is_valid = TRUE
    """, (customer_id,))
    total_spent = cursor.fetchone()[0] or 0

    # 4. Most recent order date
    cursor.execute("SELECT MAX(order_date) FROM `Order` WHERE customer_id = %s AND is_valid = TRUE", (customer_id,))
    last_order_date = cursor.fetchone()[0]

    # 5. Number of items ordered (across all orders)
    cursor.execute("""
        SELECT SUM(od.quantity)
        FROM `Order` o
        JOIN OrderDetails od ON o.order_id = od.order_id
        WHERE o.customer_id = %s AND o.is_valid = TRUE
    """, (customer_id,))
    total_items_ordered = cursor.fetchone()[0] or 0

    # 6. Favorite product category (most frequently ordered)
    cursor.execute("""
        SELECT p.category, COUNT(*) AS freq
        FROM `Order` o
        JOIN OrderDetails od ON o.order_id = od.order_id
        JOIN Product p ON od.product_id = p.product_id
        WHERE o.customer_id = %s AND o.is_valid = TRUE
        GROUP BY p.category
        ORDER BY freq DESC
        LIMIT 1
    """, (customer_id,))
    favorite_category = cursor.fetchone()
    favorite_category = favorite_category[0] if favorite_category else "N/A"

    # 7. Total number of different products bought
    cursor.execute("""
        SELECT COUNT(DISTINCT od.product_id)
        FROM `Order` o
        JOIN OrderDetails od ON o.order_id = od.order_id
        WHERE o.customer_id = %s AND o.is_valid = TRUE
    """, (customer_id,))
    unique_products = cursor.fetchone()[0] or 0

    # 8. Most purchased product
    cursor.execute("""
        SELECT p.product_name, SUM(od.quantity) AS total
        FROM `Order` o
        JOIN OrderDetails od ON o.order_id = od.order_id
        JOIN Product p ON od.product_id = p.product_id
        WHERE o.customer_id = %s AND o.is_valid = TRUE
        GROUP BY p.product_name
        ORDER BY total DESC
        LIMIT 1
    """, (customer_id,))
    top_product = cursor.fetchone()
    top_product_name = top_product[0] if top_product else "N/A"

 # 9. Customer's rank by total spending
    cursor.execute("""
    SELECT COUNT(DISTINCT total_spent) + 1 AS customer_rank FROM (
        SELECT o.customer_id, SUM(od.price * od.quantity) AS total_spent
        FROM `Order` o
        JOIN OrderDetails od ON o.order_id = od.order_id
        WHERE o.is_valid = TRUE
        GROUP BY o.customer_id
    ) AS customer_totals
    WHERE total_spent > %s
    """, (total_spent,))
    rank = cursor.fetchone()[0]



    # 10. Average order value
    cursor.execute("""
        SELECT AVG(sub.total)
        FROM (
            SELECT SUM(od.price * od.quantity) AS total
            FROM `Order` o
            JOIN OrderDetails od ON o.order_id = od.order_id
            WHERE o.customer_id = %s AND o.is_valid = TRUE
            GROUP BY o.order_id
        ) AS sub
    """, (customer_id,))
    avg_order_value = cursor.fetchone()[0] or 0

    cursor.close()
    conn.close()

    return render_template('profile.html',
                           customer=customer,
                           user_order_count=user_order_count,
                           total_spent=total_spent,
                           last_order_date=last_order_date,
                           total_items_ordered=total_items_ordered,
                           favorite_category=favorite_category,
                           unique_products=unique_products,
                           top_product_name=top_product_name,
                           rank=rank,
                           avg_order_value=avg_order_value)

@app.route('/logout')
def logout():
    session.pop('customer_id', None) # Remove customer_id from session
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'customer_id' not in session:
        flash("Please log in to continue with checkout.", "info")
        return redirect(url_for('customerlogin'))

    customer_id = session['customer_id']
    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Get cart order
        cursor.execute("SELECT order_id FROM `Order` WHERE customer_id = %s AND status = 'cart'", (customer_id,))
        cart_order = cursor.fetchone()

        if not cart_order:
            flash("Your cart is empty.", "info")
            return redirect(url_for('cart'))

        order_id = cart_order['order_id']

        # Fetch cart items
        cursor.execute("""
            SELECT od.product_id, od.quantity, od.price, p.product_name
            FROM OrderDetails od
            JOIN Product p ON od.product_id = p.product_id
            WHERE od.order_id = %s AND od.is_valid = TRUE
        """, (order_id,))
        cart_items = cursor.fetchall()
        total_price = sum(item['price'] * item['quantity'] for item in cart_items)

        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            payment_method = request.form.get('payment_method')
            amount_paid = total_price

            # Validate basic fields
            if not all([name, email, payment_method]):
                flash("Please fill in all required fields.", "error")
                return redirect(url_for('checkout'))

            if payment_method == 'card':
                card_number = request.form.get('card_number')
                expiry_date = request.form.get('expiry_date')
                cvv = request.form.get('cvv')
                if not all([card_number, expiry_date, cvv]):
                    flash("Please complete all card details.", "error")
                    return redirect(url_for('checkout'))


            # Update order status
            cursor.execute(
                "UPDATE `Order` SET status = 'confirmed', order_date = %s WHERE order_id = %s",
                (date.today(), order_id)
            )
            # Mark order details as invalid (is_valid = 0) after purchase
            cursor.execute("""
                UPDATE OrderDetails SET is_valid = 0 WHERE order_id = %s
            """, (order_id,))

            cursor.execute(
            "INSERT INTO Invoice (order_id, invoice_date) VALUES (%s, %s)",
            (order_id, date.today())
            )
            invoice_id = cursor.lastrowid  # get the new invoice_id

            # Insert payment
            cursor.execute("""
            INSERT INTO Payment (invoice_id, payment_date, amount_paid, payment_method)
            VALUES (%s, %s, %s, %s)
            """, (invoice_id, date.today(), amount_paid, payment_method))
            # Increment order_count for the customer
            cursor.execute("""
                UPDATE Customer SET order_count = order_count + 1 WHERE customer_id = %s
            """, (customer_id,))


            conn.commit()
            flash("Payment successful and order confirmed!", "success")
           

        # GET request: render checkout page
        return render_template('checkout.html', cart_items=cart_items, total_price=total_price)

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        flash("Checkout failed. Please try again.", "error")
        if conn:
            conn.rollback()
        return redirect(url_for('cart'))

    finally:
        if conn:
            conn.close()

@app.route('/delete_from_cart/<int:product_id>', methods=['POST'])
def delete_from_cart(product_id):
    if 'customer_id' not in session:
        flash("Please log in to modify your cart.", "info")
        return redirect(url_for('customerlogin'))

    customer_id = session['customer_id']
    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Get current cart order
        cursor.execute("SELECT order_id FROM `Order` WHERE customer_id = %s AND status = 'cart'", (customer_id,))
        cart_order = cursor.fetchone()

        if not cart_order:
            flash("No cart found.", "error")
            return redirect(url_for('cart'))

        order_id = cart_order['order_id']

        # Soft delete: set is_valid = FALSE in OrderDetails
        cursor.execute("""
            UPDATE OrderDetails 
            SET is_valid = FALSE 
            WHERE order_id = %s AND product_id = %s
        """, (order_id, product_id))

        conn.commit()
        flash("Item removed from cart.", "success")
        return redirect(url_for('cart'))

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        if conn:
            conn.rollback()
        flash("Could not remove item from cart.", "error")
        return redirect(url_for('cart'))

    finally:
        if conn:
            conn.close()

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
            cursor.execute("UPDATE OrderDetails SET quantity = %s WHERE order_id = %s AND product_id = %s",
                           (new_quantity, existing_item['order_id'], product_id))
            flash(f"Added another {product_info['product_name']} to cart!", "success")
        else:
            # Add new item to cart
            cursor.execute("INSERT INTO OrderDetails (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                           (order_id, product_id, quantity, product_price))
            flash(f"{product_info['product_name']} added to cart!", "success")
        
        cursor.execute("""
        UPDATE Product SET stock_quantity = stock_quantity - %s WHERE product_id = %s
        """, (quantity, product_id))
        
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
                SELECT od.product_id, od.quantity, od.price, p.product_name
                FROM OrderDetails od
                JOIN Product p ON od.product_id = p.product_id
                WHERE od.order_id = %s AND od.is_valid = TRUE
            """, (order_id,))

            cart_items = cursor.fetchall()
            total_price = sum(item['price'] * item['quantity'] for item in cart_items)

        return render_template('cart.html', cart_items=cart_items, total_price=total_price)

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        flash("Could not load cart at this time.", "error")
        return render_template('cart.html', cart_items=[], total_price=0)

    finally:
        if conn:
            conn.close()


######################## Manager ###################3
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

########## Customers in Manager base html  ###############      
@app.route('/m_customers/')
def m_customers():
    """Render the customers management page"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee")
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('managerlog'))
    
    return render_template('m_customers.html', employee=employee)

@app.route('/api/manager/customers')
def get_all_customers():
    """Get all customers with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query to show customers with their order counts
        base_query = '''
            SELECT 
                c.customer_id, 
                c.customer_name, 
                c.email_address, 
                c.phone_number,
                c.city,
                c.is_valid,
                COUNT(o.order_id) as order_count
            FROM customer c
            LEFT JOIN `order` o ON c.customer_id = o.customer_id AND o.is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'customer_id':
                conditions.append("c.customer_id = %s")
                params.append(int(search_value))
            elif search_by == 'customer_name':
                conditions.append("c.customer_name LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'email_address':
                conditions.append("c.email_address LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'phone_number':
                conditions.append("c.phone_number LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'city':
                conditions.append("c.city LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'is_valid':
                is_valid = search_value.lower() in ['true', '1', 'active']
                conditions.append("c.is_valid = %s")
                params.append(is_valid)
        
        # Build final query
        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " GROUP BY c.customer_id ORDER BY c.customer_id ASC"
        
        cursor.execute(query, params)
        customers = cursor.fetchall()
        conn.close()
        
        return jsonify(customers)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/customers', methods=['POST'])
def create_customer():
    """Create a new customer"""
    try:
        data = request.get_json()
        required_fields = ['customer_name', 'customer_password']
        
        # Validate required fields
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        
        cursor.execute("""
            INSERT INTO customer (
                customer_name, 
                email_address, 
                phone_number,
                city,
                shipping_address,
                customer_password
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data['customer_name'],
            data.get('email_address'),
            data.get('phone_number'),
            data.get('city'),
            data.get('shipping_address'),
            required_fields[1]
        ))
        
        customer_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Customer created successfully',
            'customer_id': customer_id
        }), 201
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """Update an existing customer"""
    try:
        data = request.get_json()
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First get current customer data
        cursor.execute("""
            SELECT * FROM customer 
            WHERE customer_id = %s
        """, (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Update only the fields that were provided
        update_fields = []
        params = []
        
        if 'customer_name' in data:
            update_fields.append("customer_name = %s")
            params.append(data['customer_name'])
        
        if 'email_address' in data:
            update_fields.append("email_address = %s")
            params.append(data['email_address'])
        
        if 'phone_number' in data:
            update_fields.append("phone_number = %s")
            params.append(data['phone_number'])
        
        if 'city' in data:
            update_fields.append("city = %s")
            params.append(data['city'])
        
        if 'shipping_address' in data:
            update_fields.append("shipping_address = %s")
            params.append(data['shipping_address'])
        
        if not update_fields:
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Build and execute update query
        update_query = "UPDATE customer SET " + ", ".join(update_fields) + " WHERE customer_id = %s"
        params.append(customer_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Customer updated successfully',
            'customer_id': customer_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/customers/<int:customer_id>', methods=['DELETE'])
def deactivate_customer(customer_id):
    """Deactivate a customer (soft delete)"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if customer exists
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Soft delete the customer
        cursor.execute("""
            UPDATE customer 
            SET is_valid = FALSE 
            WHERE customer_id = %s
        """, (customer_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Customer deactivated successfully',
            'customer_id': customer_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/customers/<int:customer_id>/reactivate', methods=['PUT'])
def reactivate_customer(customer_id):
    """Reactivate a customer"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if customer exists
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Reactivate the customer
        cursor.execute("""
            UPDATE customer 
            SET is_valid = TRUE 
            WHERE customer_id = %s
        """, (customer_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Customer reactivated successfully',
            'customer_id': customer_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500
    
########## Employees in Manager base html  ###############      
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
    
    return render_template('m_employees.html')

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

########## Suppliers in Manager base html  ###############      
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
        
        # Base query to show suppliers with their order counts
        base_query = '''
            SELECT 
                s.supplier_id, 
                s.supplier_name, 
                s.email_address, 
                s.phone_number,
                s.is_valid,
                COUNT(po.purchase_order_id) as order_count
            FROM supplier s
            LEFT JOIN purchaseorder po ON s.supplier_id = po.supplier_id AND po.is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'supplier_id':
                conditions.append("s.supplier_id = %s")
                params.append(int(search_value))
            elif search_by == 'supplier_name':
                conditions.append("s.supplier_name LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'email_address':
                conditions.append("s.email_address LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'phone_number':
                conditions.append("s.phone_number LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'is_valid':
                # Convert to boolean (1 for true/active, 0 for false/inactive)
                is_valid = 1 if search_value.lower() in ['true', '1', 'active'] else 0
                conditions.append("s.is_valid = %s")
                params.append(is_valid)
        else:
            # If no search, show only active suppliers by default
            conditions.append("s.is_valid = TRUE")
        
        # Build final query
        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " GROUP BY s.supplier_id ORDER BY s.supplier_id ASC"
        
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
                'order_count': supplier['order_count'],
                'is_valid': bool(supplier['is_valid'])
            })
        
        return jsonify(suppliers_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

  
@app.route('/api/manager/suppliers/<int:supplier_id>', methods=['DELETE'])
def deactivate_supplier(supplier_id):
    """Deactivate a supplier by setting is_valid to FALSE"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Check if supplier exists and is active
        cursor.execute("SELECT supplier_id FROM supplier WHERE supplier_id = %s AND is_valid = TRUE", (supplier_id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Supplier not found or already inactive'}), 404
        
        # Deactivate any related purchase orders (optional)
        # cursor.execute("""
        #    UPDATE purchaseorder 
        #    SET is_valid = FALSE 
        #    WHERE supplier_id = %s AND status = 'Pending'
        # """, (supplier_id,))
        
        # Deactivate the supplier
        cursor.execute("""
            UPDATE supplier 
            SET is_valid = FALSE 
            WHERE supplier_id = %s
        """, (supplier_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Supplier deactivated successfully',
            'supplier_id': supplier_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500
@app.route('/api/manager/suppliers/<int:supplier_id>/reactivate', methods=['PUT'])
def reactivate_supplier(supplier_id):
    """Reactivate a supplier by setting is_valid to TRUE"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if supplier exists
        cursor.execute("SELECT supplier_id, supplier_name FROM supplier WHERE supplier_id = %s", (supplier_id,))
        supplier = cursor.fetchone()
        
        if not supplier:
            conn.close()
            return jsonify({'error': 'Supplier not found'}), 404
        
        # Reactivate the supplier
        cursor.execute("""
            UPDATE supplier 
            SET is_valid = TRUE 
            WHERE supplier_id = %s
        """, (supplier_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Failed to reactivate supplier'}), 500
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Supplier "{supplier["supplier_name"]}" reactivated successfully',
            'supplier_id': supplier_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

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

########## Orders in Manager base html  ###############      

@app.route('/m_orders/')
def m_orders():
    """Render the orders management page"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (1,))  # Example: get employee with ID 1
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
        
        # Separate WHERE conditions from HAVING conditions
        where_conditions = []
        having_conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'order_id':
                where_conditions.append("o.order_id = %s")
                params.append(int(search_value))
            elif search_by == 'customer_id':
                where_conditions.append("o.customer_id = %s")
                params.append(int(search_value))
            elif search_by == 'total_price':
                # Use HAVING for aggregate functions
                having_conditions.append("COALESCE(SUM(od.price * od.quantity), 0) = %s")
                params.append(float(search_value))
            elif search_by == 'status':
                if search_value == 'cart':
                    where_conditions.append("o.actual_received_date IS NULL")
                elif search_value == 'completed':
                    where_conditions.append("o.actual_received_date IS NOT NULL AND o.actual_received_date <= o.expected_received_date")
                elif search_value == 'delayed':
                    where_conditions.append("o.actual_received_date IS NOT NULL AND o.actual_received_date > o.expected_received_date")
        
        # Build final query
        query = base_query
        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)
        
        # Add GROUP BY
        query += " GROUP BY o.order_id, o.customer_id, o.employee_id, o.order_date, o.expected_received_date, o.actual_received_date"
        
        # Add HAVING clause for aggregate conditions
        if having_conditions:
            query += " HAVING " + " AND ".join(having_conditions)
        
        query += " ORDER BY o.order_date "
        
        cursor.execute(query, params)
        orders = cursor.fetchall()
        conn.close()
        
        orders_list = []
        for order in orders:
            orders_list.append({
                'order_id': order['order_id'],
                'customer_id': order['customer_id'],
                'employee_id': order['employee_id'],
                'order_date': order['order_date'].isoformat() if order['order_date'] else None,
                'expected_received_date': order['expected_received_date'].isoformat() if order['expected_received_date'] else None,
                'actual_received_date': order['actual_received_date'].isoformat() if order['actual_received_date'] else None,
                'total_price': float(order['total_price'])
            })
        
        return jsonify(orders_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/order-details/<int:order_id>')
def get_order_details(order_id):
    """Get details for a specific order"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get order details
        query = '''
            SELECT 
                od.product_id,
                p.product_name,
                od.price,
                od.quantity
            FROM OrderDetails od
            LEFT JOIN Product p ON od.product_id = p.product_id
            WHERE od.order_id = %s AND od.is_valid = TRUE
        '''
        cursor.execute(query, (order_id,))
        details = cursor.fetchall()
        
        # Get basic order info
        cursor.execute('''
            SELECT 
                customer_id,
                order_date,
                expected_received_date,
                actual_received_date
            FROM `Order`
            WHERE order_id = %s AND is_valid = TRUE
        ''', (order_id,))
        order_info = cursor.fetchone()
        
        conn.close()
        
        if not order_info:
            return jsonify({'error': 'Order not found'}), 404
        
        details_list = []
        for detail in details:
            details_list.append({
                'product_id': detail['product_id'],
                'product_name': detail['product_name'],
                'price': float(detail['price']),
                'quantity': detail['quantity']
            })
        
        return jsonify(details_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


########## Purchase Orders in Manager base html  ###############      
@app.route('/m_p_orders/<int:employee_id>')
def m_p_orders(employee_id):
    """Render the purchase orders management page for managers"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('managerlog'))
    
    return render_template('m_p_orders.html', employee=employee)

@app.route('/api/manager/purchase-orders', methods=['GET'])
def get_purchase_orders():
    """Get all purchase orders with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query
        base_query = '''
            SELECT 
                po.purchase_order_id, 
                po.supplier_id, 
                po.employee_id, 
                po.order_date,
                po.expected_received_date,
                po.actual_received_date,
                po.delivery_status,
                po.is_valid
            FROM purchaseorder po
            WHERE 1=1
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'purchase_order_id':
                conditions.append("po.purchase_order_id = %s")
                params.append(int(search_value))
            elif search_by == 'supplier_id':
                conditions.append("po.supplier_id = %s")
                params.append(int(search_value))
            elif search_by == 'employee_id':
                conditions.append("po.employee_id = %s")
                params.append(int(search_value))
            elif search_by == 'delivery_status':
                conditions.append("po.delivery_status = %s")
                params.append(search_value.lower())
            elif search_by == 'is_valid':
                if search_value.lower() == 'true':
                    conditions.append("po.is_valid = TRUE")
                elif search_value.lower() == 'false':
                    conditions.append("po.is_valid = FALSE")
        
        # Build final query
        query = base_query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY po.order_date "
        
        cursor.execute(query, params)
        purchase_orders = cursor.fetchall()
        conn.close()
        
        purchase_orders_list = []
        for po in purchase_orders:
            purchase_orders_list.append({
                'purchase_order_id': po['purchase_order_id'],
                'supplier_id': po['supplier_id'],
                'employee_id': po['employee_id'],
                'order_date': po['order_date'].strftime('%Y-%m-%d') if po['order_date'] else None,
                'expected_received_date': po['expected_received_date'].strftime('%Y-%m-%d') if po['expected_received_date'] else None,
                'actual_received_date': po['actual_received_date'].strftime('%Y-%m-%d') if po['actual_received_date'] else None,
                'delivery_status': po['delivery_status'],
                'is_valid': po['is_valid']
            })
        
        return jsonify(purchase_orders_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/purchase-order-details/<int:purchase_order_id>', methods=['GET'])
def get_purchase_order_details(purchase_order_id):
    """Get details for a specific purchase order"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get the products in this purchase order
        cursor.execute('''
            SELECT 
                pod.product_id,
                p.product_name,
                pod.price,
                pod.quantity
            FROM purchaseorderdetails pod
            JOIN product p ON pod.product_id = p.product_id
            WHERE pod.purchase_order_id = %s AND pod.is_valid = TRUE
        ''', (purchase_order_id,))
        
        details = cursor.fetchall()
        conn.close()
        
        details_list = []
        for item in details:
            details_list.append({
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'price': float(item['price']),
                'quantity': item['quantity']
            })
        
        return jsonify(details_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/purchase-orders/<int:purchase_order_id>/status', methods=['PUT'])
def update_purchase_order_status(purchase_order_id):
    """Update the status of a purchase order"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        received_date = data.get('received_date')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Check if purchase order exists and is valid
        cursor.execute("SELECT purchase_order_id FROM purchaseorder WHERE purchase_order_id = %s AND is_valid = TRUE", (purchase_order_id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Purchase order not found or inactive'}), 404
        
        # Update the status
        update_query = "UPDATE purchaseorder SET delivery_status = %s"
        params = [new_status]
        
        if new_status == 'Received' and received_date:
            update_query += ", actual_received_date = %s"
            params.append(received_date)
            
            # Update stock quantities for Received products
            cursor.execute('''
                SELECT product_id, quantity 
                FROM purchaseorderdetails 
                WHERE purchase_order_id = %s AND is_valid = TRUE
            ''', (purchase_order_id,))
            
            products = cursor.fetchall()
            
            for product in products:
                cursor.execute('''
                    UPDATE product 
                    SET stock_quantity = stock_quantity + %s,
                        stock_arrival_date = %s
                    WHERE product_id = %s
                ''', (product['quantity'], received_date, product['product_id']))
        
        update_query += " WHERE purchase_order_id = %s"
        params.append(purchase_order_id)
        
        cursor.execute(update_query, params)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Purchase order status updated successfully',
            'purchase_order_id': purchase_order_id,
            'new_status': new_status
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/suppliers/<int:supplier_id>/check', methods=['GET'])
def check_supplier(supplier_id):
    """Check if a supplier exists and is valid"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT supplier_id, is_valid 
            FROM supplier 
            WHERE supplier_id = %s
        """, (supplier_id,))
        
        supplier = cursor.fetchone()
        conn.close()
        
        if not supplier:
            return jsonify({
                'exists': False,
                'is_valid': False
            })
        
        return jsonify({
            'exists': True,
            'is_valid': supplier['is_valid']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
  
@app.route('/api/manager/purchase-orders', methods=['POST'])
def create_purchase_order():
    """Create a new purchase order"""
    try:
        data = request.get_json()
        supplier_id = data.get('supplier_id')
        employee_id = data.get('employee_id')
        expected_received_date = data.get('expected_received_date')
        products = data.get('products')
        
        if not supplier_id or not employee_id or not expected_received_date or not products:
            return jsonify({'error': 'Supplier ID, employee ID, expected date, and products are required'}), 400
        
        if not isinstance(products, list) or len(products) == 0:
            return jsonify({'error': 'At least one product is required'}), 400
        
        # Validate expected date is in the future
        expected_date = datetime.strptime(expected_received_date, '%Y-%m-%d').date()
        if expected_date <= datetime.now().date():
            return jsonify({'error': 'Expected delivery date must be after the current date'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Verify supplier exists and is valid
        cursor.execute("""
            SELECT supplier_id 
            FROM supplier 
            WHERE supplier_id = %s AND is_valid = TRUE
        """, (supplier_id,))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Supplier does not exist or is inactive'}), 400
        
        # Create the purchase order
        # Correct the parameter in the purchase order details insertion
        cursor.execute('''
            INSERT INTO purchaseorderdetails (
                purchase_order_id,
                product_id,
                price,
                quantity,
                employee_id,
                is_valid
            )
            VALUES (%s, %s, %s, %s, %s, TRUE)
        ''', (purchase_order_id, product['product_id'], product['price'], product['quantity'], employee_id))
            
        purchase_order_id = cursor.lastrowid
        
        # Add products to the purchase order
        for product in products:
            cursor.execute('''
                INSERT INTO purchaseorderdetails (
                    purchase_order_id,
                    product_id,
                    price,
                    quantity,
                    employee_id,
                    is_valid
                )
                VALUES (%s, %s, %s, %s, TRUE)
            ''', (purchase_order_id, product['product_id'], product['price'], product['quantity'], product[1]))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Purchase order created successfully',
            'purchase_order_id': purchase_order_id
        }), 201
    
    except ValueError as e:
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/purchase-orders/<int:purchase_order_id>', methods=['DELETE'])
def soft_delete_purchase_order(purchase_order_id):
    """Soft delete a purchase order by setting is_valid to False"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Check if purchase order exists and is pending
        cursor.execute("""
            SELECT purchase_order_id 
            FROM purchaseorder 
            WHERE purchase_order_id = %s 
            AND delivery_status = 'pending'
            AND is_valid = TRUE
        """, (purchase_order_id,))
        
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Pending purchase order not found or already inactive'}), 404
        
        # Soft delete the purchase order
        cursor.execute("""
            UPDATE purchaseorder 
            SET is_valid = FALSE 
            WHERE purchase_order_id = %s
        """, (purchase_order_id,))
        
        # Soft delete the purchase order details
        cursor.execute("""
            UPDATE purchaseorderdetails 
            SET is_valid = FALSE 
            WHERE purchase_order_id = %s
        """, (purchase_order_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Purchase order deleted successfully',
            'purchase_order_id': purchase_order_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/purchase-orders/<int:purchase_order_id>/reactivate', methods=['PUT'])
def reactivate_purchase_order(purchase_order_id):
    """Reactivate a soft-deleted purchase order by setting is_valid to True"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Check if purchase order exists and is inactive
        cursor.execute("""
            SELECT purchase_order_id 
            FROM purchaseorder 
            WHERE purchase_order_id = %s 
            AND is_valid = FALSE
        """, (purchase_order_id,))
        
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Purchase order not found or already active'}), 404
        
        # Reactivate the purchase order
        cursor.execute("""
            UPDATE purchaseorder 
            SET is_valid = TRUE 
            WHERE purchase_order_id = %s
        """, (purchase_order_id,))
        
        # Reactivate the purchase order details
        cursor.execute("""
            UPDATE purchaseorderdetails 
            SET is_valid = TRUE 
            WHERE purchase_order_id = %s
        """, (purchase_order_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Purchase order reactivated successfully',
            'purchase_order_id': purchase_order_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500
    
########## Products in Manager base html  ###############      
@app.route('/m_products/')
def m_products():
    """Render the products management page"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM Employee", )
    employee = cursor.fetchone()
    conn.close()
    
    if not employee:
        return redirect(url_for('emplog'))
    
    return render_template('m_products.html', employee=employee)

@app.route('/api/manager/products')
def get_all_products():
    """Get all products with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query
        base_query = '''
            SELECT 
                p.product_id, 
                p.product_name, 
                p.category, 
                p.price,
                p.stock_quantity,
                p.stock_arrival_date,
                p.is_valid
            FROM product p
        '''
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_by and search_value:
            if search_by == 'product_id':
                conditions.append("p.product_id = %s")
                params.append(int(search_value))
            elif search_by == 'product_name':
                conditions.append("p.product_name LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'category':
                conditions.append("p.category LIKE %s")
                params.append(f'%{search_value}%')
            elif search_by == 'price':
                conditions.append("p.price = %s")
                params.append(float(search_value))
            elif search_by == 'stock_quantity':
                conditions.append("p.stock_quantity = %s")
                params.append(int(search_value))
            elif search_by == 'is_valid':
                # Convert to boolean (1 for true/active, 0 for false/inactive)
                is_valid = 1 if search_value.lower() in ['true', '1', 'active'] else 0
                conditions.append("p.is_valid = %s")
                params.append(is_valid)
        else:
            # If no search, show only active products by default
            conditions.append("p.is_valid = TRUE")
        
        # Build final query
        query = base_query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY p.product_id ASC"
        
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
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Check if product exists and is active
        cursor.execute("SELECT product_id FROM product WHERE product_id = %s AND is_valid = TRUE", (product_id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Product not found or already inactive'}), 404
        
        # Deactivate the product
        cursor.execute("""
            UPDATE product 
            SET is_valid = FALSE 
            WHERE product_id = %s
        """, (product_id,))
        
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

@app.route('/api/manager/products/<int:product_id>/reactivate', methods=['PUT'])
def reactivate_product(product_id):
    """Reactivate a product by setting is_valid to TRUE"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if product exists
        cursor.execute("SELECT product_id, product_name FROM product WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        # Reactivate the product
        cursor.execute("""
            UPDATE product 
            SET is_valid = TRUE 
            WHERE product_id = %s
        """, (product_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Failed to reactivate product'}), 500
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Product "{product["product_name"]}" reactivated successfully',
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
        required_fields = ['product_name', 'category', 'price', 'stock_quantity']
        
        # Validate required fields
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            INSERT INTO product (
                product_name, 
                category, 
                price, 
                stock_quantity, 
                stock_arrival_date, 
                is_valid
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data['product_name'],
            data['category'],
            data['price'],
            data['stock_quantity'],
            data.get('stock_arrival_date'),
            data.get('is_valid', True)
        ))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product created successfully',
            'product_id': product_id
        }), 201
    
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
            SELECT * FROM product 
            WHERE product_id = %s AND is_valid = TRUE
        """, (product_id,))
        product = cursor.fetchone()
        
        if not product:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
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
            update_fields.append("price = %s")
            params.append(data['price'])
        
        if 'stock_quantity' in data:
            update_fields.append("stock_quantity = %s")
            params.append(data['stock_quantity'])
        
        if 'stock_arrival_date' in data:
            update_fields.append("stock_arrival_date = %s")
            params.append(data['stock_arrival_date'])
        
        if 'is_valid' in data:
            update_fields.append("is_valid = %s")
            params.append(data['is_valid'])
        
        if not update_fields:
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Build and execute update query
        update_query = "UPDATE product SET " + ", ".join(update_fields) + " WHERE product_id = %s"
        params.append(product_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Product updated successfully',
            'product_id': product_id
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500
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

########## Report in Manager base html  ###############      
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
    e.emp_role
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


    cursor.execute("""
    SELECT c.customer_id, c.customer_name, SUM(od.price * od.quantity) AS total_spent
    FROM Customer c, `Order` o,OrderDetails od 
    WHERE c.customer_id = o.customer_id AND o.order_id = od.order_id
    AND c.is_valid = TRUE AND o.is_valid = TRUE
    GROUP BY c.customer_id, c.customer_name
    ORDER BY total_spent DESC
    LIMIT 4;
    """)
    customer_q1 = cursor.fetchall()

    # Purchase orders
    cursor.execute("""
        SELECT s.supplier_name, p.purchase_order_id, p.order_date, p.delivery_status
        FROM PurchaseOrder p, Supplier s  
        WHERE p.supplier_id = s.supplier_id AND p.is_valid = TRUE AND s.is_valid = TRUE
        ORDER BY p.order_date ASC
        LIMIT 3
    """)
    purchase_orders = cursor.fetchall()

    # Salary summary
    cursor.execute("""
        SELECT e.employee_name, 'Hourly' AS type, 
               CONCAT('$', he.hourly_wages) AS salary_or_wage,
               CONCAT('$', (he.hours_worked * he.hourly_wages)) AS total_wage
        FROM HourlyEmployee he, Employee e 
        WHERE he.is_valid = TRUE AND he.employee_id = e.employee_id

        UNION

        SELECT e.employee_name, 'Contract' AS type, 
               CONCAT('$', c.salary) AS salary_or_wage,
               NULL AS total_pay
        FROM ContractEmployee ce, Contract c, Employee e 
        WHERE ce.is_valid = TRUE AND c.is_valid = TRUE AND ce.contract_id = c.contract_id AND ce.employee_id = e.employee_id
    """)
    salary_data = cursor.fetchall()

    cursor.execute("SELECT * FROM Employee WHERE emp_role LIKE '%Manager%' LIMIT 1")
    employee = cursor.fetchone()
    

    # Product ordered the most by quantity
    cursor.execute("""
    SELECT P.product_name, SUM(OD.quantity) AS total_quantity_sold
    FROM OrderDetails OD
    JOIN Product P ON OD.product_id = P.product_id
    WHERE OD.is_valid = TRUE AND P.is_valid = TRUE
    GROUP BY P.product_name
    HAVING SUM(OD.quantity) >= ALL (
        SELECT SUM(quantity)
        FROM OrderDetails
        WHERE is_valid = TRUE
        GROUP BY product_id
    )
    """)
    top_product = cursor.fetchone()

    ''' 
        cursor.execute("""
            SELECT DISTINCT P.product_name 
            FROM OrderDetails OD 
            JOIN Product P ON OD.product_id = P.product_id 
            WHERE OD.is_valid = 1 AND OD.price = (
                SELECT MIN(price) 
                FROM OrderDetails
                WHERE is_valid = TRUE
            )
        """)
        lowest_price_product = cursor.fetchone()

        cursor.execute("""
            SELECT 
                c.customer_id,
                c.customer_name,
                COUNT(DISTINCT o.order_id) AS total_orders,
                SUM(od.price * od.quantity) AS total_amount_spent
            FROM 
                Customer c
            JOIN `Order` o ON c.customer_id = o.customer_id
            JOIN OrderDetails od ON o.order_id = od.order_id
            WHERE o.is_valid = 1 AND od.is_valid = 1
            GROUP BY c.customer_id, c.customer_name
            ORDER BY total_amount_spent DESC
        """)
        customer_spending = cursor.fetchall()
    '''


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
        salary_data=salary_data, 
        top_product = top_product, 
    )

################## Employee ############################

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
@app.route('/emp/<int:employee_id>/Eprofile') 
def emp(employee_id, Eprofile=False):
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
    
    if request.path.endswith('/Eprofile') or request.args.get('Eprofile'):
        cursor.execute("SELECT * FROM HourlyEmployee WHERE employee_id = %s", (employee_id,))
        hourly_data = cursor.fetchone()
        
        cursor.execute("SELECT * FROM ContractEmployee WHERE employee_id = %s", (employee_id,))
        contract_data = cursor.fetchone()
    
    conn.close()
    
    # Determine which template to render
    if request.path.endswith('/Eprofile') or request.args.get('Eprofile'):
        return render_template('emp.html', 
                            employee=employee,
                            hourly_data=hourly_data,
                            contract_data=contract_data,
                            show_profile=True)
    else:
        return render_template('emp.html', employee=employee)
     
########## Orders in Emp base html  ###############      
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

@app.route('/api/employees/<int:employee_id>/orders', methods=['GET'])
def get_employee_orders(employee_id):
    """Get all orders for a specific employee with optional search filtering"""
    try:
        search_by = request.args.get('search_by')
        search_value = request.args.get('search_value')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query
        base_query = '''
            SELECT 
                o.order_id, 
                o.customer_id, 
                o.employee_id, 
                o.order_date,
                o.expected_received_date,
                o.actual_received_date,
                o.status,
                o.is_valid,
                (SELECT SUM(od.price * od.quantity) 
                 FROM orderdetails od 
                 WHERE od.order_id = o.order_id AND od.is_valid = TRUE) as total_price
            FROM `order` o
            WHERE o.employee_id = %s AND o.is_valid = TRUE
        '''
        
        # Add search conditions
        conditions = []
        params = [employee_id]
        
        if search_by and search_value:
            if search_by == 'order_id':
                conditions.append("o.order_id = %s")
                params.append(int(search_value))
            elif search_by == 'customer_id':
                conditions.append("o.customer_id = %s")
                params.append(int(search_value))
            elif search_by == 'status':
                conditions.append("o.status = %s")
                params.append(search_value.lower())
            elif search_by == 'total_price':
                conditions.append("(SELECT SUM(od.price * od.quantity) FROM orderdetails od WHERE od.order_id = o.order_id) = %s")
                params.append(float(search_value))
        
        # Build final query
        query = base_query
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY o.order_date DESC"
        
        cursor.execute(query, params)
        orders = cursor.fetchall()
        conn.close()
        
        orders_list = []
        for order in orders:
            orders_list.append({
                'order_id': order['order_id'],
                'customer_id': order['customer_id'],
                'employee_id': order['employee_id'],
                'order_date': order['order_date'].strftime('%Y-%m-%d') if order['order_date'] else None,
                'expected_received_date': order['expected_received_date'].strftime('%Y-%m-%d') if order['expected_received_date'] else None,
                'actual_received_date': order['actual_received_date'].strftime('%Y-%m-%d') if order['actual_received_date'] else None,
                'status': order['status'],
                'total_price': float(order['total_price']) if order['total_price'] else 0.00,
                'is_valid': order['is_valid']
            })
        
        return jsonify(orders_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees/<int:employee_id>/order-details/<int:order_id>', methods=['GET'])
def get_employee_order_details(employee_id, order_id):
    """Get details for a specific order that belongs to an employee"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First verify the order belongs to this employee
        cursor.execute('''
            SELECT order_id FROM `order` 
            WHERE order_id = %s AND employee_id = %s AND is_valid = TRUE
        ''', (order_id, employee_id))
        
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Order not found or not assigned to this employee'}), 404
        
        # Get the products in this order
        cursor.execute('''
            SELECT 
                od.product_id,
                p.product_name,
                od.price,
                od.quantity
            FROM orderdetails od
            JOIN product p ON od.product_id = p.product_id
            WHERE od.order_id = %s AND od.is_valid = TRUE
        ''', (order_id,))
        
        details = cursor.fetchall()
        conn.close()
        
        details_list = []
        for item in details:
            details_list.append({
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'price': float(item['price']),
                'quantity': item['quantity']
            })
        
        return jsonify(details_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees/<int:employee_id>/orders/<int:order_id>/status', methods=['PUT'])
def update_employee_order_status(employee_id, order_id):
    """Update the status of an order (for employee's own orders)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        received_date = data.get('received_date')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Check if order exists, is valid, and belongs to this employee
        cursor.execute('''
            SELECT order_id FROM `order` 
            WHERE order_id = %s AND employee_id = %s AND is_valid = TRUE
        ''', (order_id, employee_id))
        
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'error': 'Order not found, inactive, or not assigned to this employee'}), 404
        
        # Update the status
        update_query = "UPDATE `order` SET status = %s"
        params = [new_status]
        
        if new_status.lower() == 'completed' and received_date:
            update_query += ", actual_received_date = %s"
            params.append(received_date)
        
        update_query += " WHERE order_id = %s"
        params.append(order_id)
        
        cursor.execute(update_query, params)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order_id': order_id,
            'new_status': new_status
        })
    
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
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
            WHERE is_valid = TRUE
            ORDER BY product_id
    ''')
    products = cursor.fetchall()
    conn.close()
    
    return render_template('e_products.html', employee=employee, products=products)

@app.route('/e_reports/<int:employee_id>')
def e_reports(employee_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Employee basic info
    cursor.execute("""
        SELECT * FROM Employee 
        WHERE employee_id = %s AND is_valid = TRUE
    """, (employee_id,))
    employee = cursor.fetchone()

    # Total orders handled by the employee
    cursor.execute("""
        SELECT COUNT(*) AS total_orders_handled
        FROM `Order`
        WHERE employee_id = %s AND is_valid = TRUE
    """, (employee_id,))
    total_orders_handled = cursor.fetchone()['total_orders_handled']

    # Total sales value handled by the employee
    cursor.execute("""
        SELECT SUM(od.price * od.quantity) AS total_sales_value
        FROM `Order` o, OrderDetails od 
        WHERE o.order_id = od.order_id AND o.employee_id = %s AND o.is_valid = TRUE AND od.is_valid = TRUE
    """, (employee_id,))
    total_sales_value = cursor.fetchone()['total_sales_value'] or 0

    # Purchase orders made by the employee
    cursor.execute("""
        SELECT po.purchase_order_id, s.supplier_name, po.order_date, po.delivery_status
        FROM PurchaseOrder po, Supplier s  
        WHERE po.supplier_id = s.supplier_id AND po.employee_id = %s AND po.is_valid = TRUE
        ORDER BY po.order_date DESC
    """, (employee_id,))
    purchase_orders = cursor.fetchall()

    # Orders with product details
    cursor.execute("""
        SELECT o.order_id, o.order_date, p.product_name, od.quantity, od.price, (od.quantity * od.price) AS total_value
        FROM `Order` o, OrderDetails od, Product p 
        WHERE o.order_id = od.order_id AND od.product_id = p.product_id AND o.employee_id = %s AND o.is_valid = TRUE AND od.is_valid = TRUE
        ORDER BY o.order_date DESC
    """, (employee_id,))
    handled_orders = cursor.fetchall()

    # Determine employee type: Hourly or Contract
    cursor.execute("""
        SELECT 'Hourly' AS type, he.hourly_wages AS salary_or_wage, he.hours_worked, (he.hourly_wages * he.hours_worked) AS total_pay
        FROM HourlyEmployee he
        WHERE he.employee_id = %s AND he.is_valid = TRUE
    """, (employee_id,))
    hourly = cursor.fetchone()

    cursor.execute("""
        SELECT 'Contract' AS type, c.salary AS salary_or_wage, NULL AS hours_worked, NULL AS total_pay
        FROM ContractEmployee ce, Contract c  
        WHERE ce.contract_id = c.contract_id AND ce.employee_id = %s AND ce.is_valid = TRUE AND c.is_valid = TRUE
    """, (employee_id,))
    contract = cursor.fetchone()

    salary_info = hourly or contract

    # Get the minimum order item value
    cursor.execute("""
        SELECT MIN(price * quantity) AS min_value
        FROM OrderDetails
        WHERE is_valid = TRUE
    """)
    min_value = cursor.fetchone()['min_value']

    # Get employees who handled orders with that minimum value
    cursor.execute("""
        SELECT DISTINCT E.employee_name, O.order_id, (OD.price * OD.quantity) AS order_value
        FROM `Order` O
        JOIN OrderDetails OD ON O.order_id = OD.order_id
        JOIN Employee E ON O.employee_id = E.employee_id
        WHERE (OD.price * OD.quantity) = %s
        AND O.is_valid = TRUE AND OD.is_valid = TRUE
    """, (min_value,))
    employees = cursor.fetchall()

    # Avg order value per employee
    cursor.execute("""
        SELECT E.employee_name, AVG(OD.price * OD.quantity) AS avg_order_value
        FROM Employee E
        JOIN `Order` O ON E.employee_id = O.employee_id
        JOIN OrderDetails OD ON O.order_id = OD.order_id
        WHERE O.is_valid = TRUE AND OD.is_valid = TRUE
        GROUP BY E.employee_name
        ORDER BY E.employee_name
    """)
    avg_order_values = cursor.fetchall()


    # Employee(s) with most valid orders
    cursor.execute("""
        SELECT E.employee_name, COUNT(*) AS order_count
        FROM `Order` O
        JOIN Employee E ON O.employee_id = E.employee_id
        WHERE O.is_valid = TRUE
        GROUP BY E.employee_name
        HAVING COUNT(*) >= ALL (
            SELECT COUNT(*)
            FROM `Order`
            WHERE is_valid = TRUE
            GROUP BY employee_id
        )
    """)
    top_order_employees = cursor.fetchall()

    conn.close()

    return render_template("e_reports.html",
        employee=employee,
        total_orders_handled=total_orders_handled,
        total_sales_value=total_sales_value,
        purchase_orders=purchase_orders,
        handled_orders=handled_orders,
        salary_info=salary_info,
        min_value=min_value,
        employees=employees,
        avg_order_values=avg_order_values,
        top_order_employees=top_order_employees
    )



if __name__ == '__main__':
    app.run(debug=True)
