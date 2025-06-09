from datetime import date
from flask import Flask, flash, render_template, request, redirect, url_for, session
import mysql
from db import get_connection

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


@app.route('/managerlog')
def managerlog():
    return render_template('managerlog.html')

@app.route('/emplog')
def emplog():
    return render_template('emplog.html')

if __name__ == '__main__':
    app.run(debug=True)
