drop database if exists electronics_store;
create database electronics_store;
USE electronics_store;

CREATE TABLE Customer (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    email_address VARCHAR(100),
    city VARCHAR(50),
    shipping_address VARCHAR(200) NOT NULL,
    order_count INT DEFAULT 0 CHECK (order_count >= 0),
    Customer_password VARCHAR(100) NOT NULL,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE Employee (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100) NOT NULL,
    emp_role VARCHAR(50),
    phone_number VARCHAR(20),
    email_address VARCHAR(100),
    hire_date DATE,
    manager_id INT default -1,
    password VARCHAR(20),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (manager_id) REFERENCES Employee(employee_id)
);

CREATE TABLE HourlyEmployee (
    employee_id INT PRIMARY KEY,
    hours_worked INT NOT NULL CHECK (hours_worked >= 0),
    hourly_wages DECIMAL(10,2) NOT NULL CHECK (hourly_wages > 0),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
);

CREATE TABLE ContractEmployee (
    employee_id INT PRIMARY KEY,
    contract_id INT NOT NULL,
    contract_start_date DATE NOT NULL,
    contract_end_date DATE NOT NULL,
    salary DECIMAL(10,2) NOT NULL CHECK (salary > 0),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
);

CREATE TABLE Product (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    stock_quantity INT NOT NULL CHECK (stock_quantity >= 0),
    stock_arrival_date DATE
);

CREATE TABLE Product_Archive (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10,2),
    stock_quantity INT,
    stock_arrival_date DATE,
    archived_at DATETIME DEFAULT NOW() 
);

CREATE TABLE `Order` (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    employee_id INT,
    total_price DECIMAL(10,2) NOT NULL CHECK (total_price >= 0),
    order_date DATE NOT NULL,
    expected_received_date DATE,
    actual_received_date DATE,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
);

CREATE TABLE OrderDetails (
    order_id INT,
    product_id INT,
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    quantity INT NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, product_id),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (order_id) REFERENCES `Order`(order_id) on delete cascade,
    FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

CREATE TABLE Supplier (
    supplier_id INT PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    email_address VARCHAR(100),
    phone_number VARCHAR(20),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE PurchaseOrder (
    purchase_order_id INT PRIMARY KEY,
    employee_id INT NOT NULL,
    supplier_id INT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL CHECK (total_price >= 0),
    order_date DATE NOT NULL,
    expected_received_date DATE,
    actual_received_date DATE,
    delivery_status VARCHAR(50) DEFAULT 'Pending' 
        CHECK (delivery_status IN ('Pending', 'Shipped', 'Received')),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id)
);

CREATE TABLE PurchaseOrderDetails (
    purchase_order_id INT,
    product_id INT,
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    quantity INT NOT NULL CHECK (quantity > 0),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (purchase_order_id, product_id),
    FOREIGN KEY (purchase_order_id) REFERENCES PurchaseOrder(purchase_order_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

CREATE TABLE Invoice (
    invoice_id INT PRIMARY KEY,
    order_id INT NOT NULL,
    invoice_date DATE NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (order_id) REFERENCES `Order`(order_id)
);

CREATE TABLE Payment (
    payment_id INT PRIMARY KEY,
    invoice_id INT NOT NULL,
    payment_date DATE NOT NULL,
    amount_paid DECIMAL(10,2) NOT NULL CHECK (amount_paid >= 0),
    payment_method VARCHAR(50) NOT NULL,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (invoice_id) REFERENCES Invoice(invoice_id)
);

INSERT INTO Customer (customer_id, customer_name, phone_number, email_address, city, shipping_address, order_count, Customer_password) 
VALUES 
(1, 'Alice Johnson', '555-1234', 'alice.johnson@email.com', 'New York', '123 Elm St, New York, NY', 5, '123'),
(2, 'Bob Smith', '555-5678', 'bob.smith@email.com', 'Los Angeles', '456 Oak St, Los Angeles, CA', 3, '123'),
(3, 'Charlie Brown', '555-8765', 'charlie.brown@email.com', 'Chicago', '789 Pine St, Chicago, IL', 7, '123');

INSERT INTO Employee (employee_id, employee_name, emp_role, phone_number, email_address, hire_date, manager_id)
VALUES
(1, 'David Williams', 'Manager', '555-1111', 'david.williams@email.com', '2021-06-01', NULL),
(2, 'Emily Davis', 'Salesperson', '555-2222', 'emily.davis@email.com', '2022-07-10', 1),
(3, 'Frank Harris', 'Salesperson', '555-3333', 'frank.harris@email.com', '2022-08-15', 1);

INSERT INTO HourlyEmployee (employee_id, hours_worked, hourly_wages)
VALUES
(2, 40, 15.00),
(3, 38, 16.50);

INSERT INTO ContractEmployee (employee_id, contract_id, contract_start_date, contract_end_date, salary)
VALUES
(3, 1001, '2023-01-01', '2023-12-31', 50000.00);

INSERT INTO Product (product_id, product_name, category, price, stock_quantity, stock_arrival_date)
VALUES
(1, 'Laptop', 'Electronics', 999.99, 25, '2024-03-15'),
(2, 'Smartphone', 'Electronics', 599.99, 50, '2024-02-10'),
(3, 'Headphones', 'Accessories', 129.99, 100, '2024-01-25'),
(4, 'Smartwatch', 'Accessories', 199.99, 75, '2024-02-01');

INSERT INTO `Order` (order_id, customer_id, employee_id, total_price, order_date, expected_received_date, actual_received_date)
VALUES
(1, 1, 2, 1599.97, '2024-04-01', '2024-04-05', '2024-04-04'),
(2, 2, 3, 599.99, '2024-04-02', '2024-04-06', '2024-04-05');

INSERT INTO OrderDetails ( order_id, product_id, price, quantity)
VALUES
(1, 1, 999.99, 1),
(1, 3, 129.99, 2),
(2, 2, 599.99, 1);

INSERT INTO Supplier (supplier_id, supplier_name, email_address, phone_number)
VALUES
(1, 'Tech Supplies Co.', 'supplier1@email.com', '555-0001'),
(2, 'Gadget Distributors', 'supplier2@email.com', '555-0002');

INSERT INTO PurchaseOrder (purchase_order_id, employee_id, supplier_id, total_price, order_date, expected_received_date, actual_received_date)
VALUES
(1, 1, 1, 25000.00, '2024-03-15', '2024-03-25', '2024-03-24'),
(2, 2, 2, 15000.00, '2024-03-18', '2024-03-28', '2024-03-27');

INSERT INTO PurchaseOrderDetails ( purchase_order_id, product_id, price, quantity)
VALUES
( 1, 1, 999.99, 20),
(1, 2, 599.99, 30),
( 2, 3, 129.99, 50);

INSERT INTO Invoice (invoice_id, order_id, invoice_date, total_amount)
VALUES
(1, 1, '2024-04-04', 1599.97),
(2, 2, '2024-04-05', 599.99);

INSERT INTO Payment (payment_id, invoice_id, payment_date, amount_paid, payment_method)
VALUES
(1, 1, '2024-04-04', 1599.97, 'Credit Card'),
(2, 2, '2024-04-05', 599.99, 'PayPal');

show tables;
SHOW DATABASES;
SELECT * FROM electronics_store.product;
SELECT * FROM electronics_store.Product_Archive;

INSERT INTO Product (product_id, product_name, category, price, stock_quantity, stock_arrival_date)
VALUES
(9, 'mic', 'Electronics', 99.99, 50, '2024-03-15'),
(6, 'mouse', 'Accessories', 199.99, 150, '2024-02-10');

