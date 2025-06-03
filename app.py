from datetime import date
from flask import Flask, render_template, request, redirect, url_for
import mysql
from db import get_connection

app = Flask(__name__)

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


@app.route('/product')
def product():
    return render_template('product.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/customerlog')
def customerlog():
    return render_template('customerlog.html')




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
            WHERE employee_id = %s AND employee_id IN (
                SELECT DISTINCT manager_id FROM Employee WHERE manager_id IS NOT NULL
            )
        """
        cursor.execute(query, (manager_id,))
        manager = cursor.fetchone()
        cursor.close()
        conn.close()

        if manager:
            if password == '1234':  
                #session['user_id'] = manager['employee_id']
                #session['role'] = 'manager'
                #flash('Welcome, Manager!', 'success')
                return render_template('manager.html')
            else:
                #flash('Incorrect password', 'danger')
                return redirect(url_for('managerlog'))
        else:
            #flash('Manager not found or not authorized', 'warning')
            return redirect(url_for('managerlog'))

    return render_template('managerlog.html')


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
        print(emp)

        cursor.close()
        conn.close()

        if emp:
            if password == '1234':  
                return render_template('emp.html')
            else:
                print("wrong pass")
                return redirect(url_for('emplog'))  
        else:
            print("No such an employee")
            return redirect(url_for('emplog'))

     return render_template('emplog.html')


@app.route('/saleslog')
def saleslog():
    return render_template('saleslog.html')

if __name__ == '__main__':
    app.run(debug=True)
