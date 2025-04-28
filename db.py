import mysql.connector

def get_connection():
    connection = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="1220212",
        database="electronics_store"
    )
    return connection
