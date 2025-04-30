from flask import Flask, render_template, request, redirect, url_for
from db import get_connection
from datetime import date

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
        data = (
            request.form['product_id'],
            request.form['product_name'],
            request.form['category'],
            request.form['price'],
            request.form['stock_quantity'],
            request.form['stock_arrival_date'],
            date.today()  # Add the current date here
        )
        conn = get_connection()
        cursor = conn.cursor()   
        cursor.execute(
            "INSERT INTO electronics_store.Product_Archive (product_id, product_name, category, price, stock_quantity, stock_arrival_date, archived_at) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
            data  # Pass the tuple with date today as part of the data
        )
        
        cursor.execute("DELETE FROM Product WHERE product_id = %s", (product_id,))  # Correct SQL syntax
        conn.commit()
        conn.close()

        return redirect(url_for('home'))
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

if __name__ == '__main__':
    app.run(debug=True)
