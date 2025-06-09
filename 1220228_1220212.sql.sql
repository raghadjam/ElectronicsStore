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
    emp_role VARCHAR(50) CHECK (emp_role IN ('Manager',  'Assistant Manager', 'Customer Service', 'Procurement Specialist', 'Inventory Specialist')),
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

CREATE TABLE Contract (
    contract_id INT PRIMARY KEY,
    contract_start_date DATE NOT NULL,
    contract_end_date DATE NOT NULL,
    salary DECIMAL(10,2) NOT NULL CHECK (salary > 0),
    is_valid BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE ContractEmployee (
    employee_id INT PRIMARY KEY,
    contract_id INT NOT NULL,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
    FOREIGN KEY (contract_id) REFERENCES Contract(contract_id)
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

INSERT INTO Employee (employee_id, employee_name, emp_role, phone_number, email_address, hire_date, manager_id, password)
VALUES
    (1, 'David Williams', 'Manager', '555-1111', 'david.williams@email.com', '2021-06-01', NULL, 'mgr123'),
    (2, 'Emily Davis', 'Customer Service', '555-2222', 'emily.davis@email.com', '2022-07-10', 1, 'emp222'),
    (3, 'Frank Harris', 'Customer Service', '555-3333', 'frank.harris@email.com', '2022-08-15', 1, 'emp333'),
    (4, 'Grace Thompson', 'Assistant Manager', '555-4444', 'grace.thompson@email.com', '2021-09-15', 1, 'emp444'),
    (5, 'Henry Clark', 'Inventory Specialist', '555-5555', 'henry.clark@email.com', '2023-01-20', 4, 'emp555'),
    (6, 'Iris Rodriguez', 'Inventory Specialist', '555-6666', 'iris.rodriguez@email.com', '2023-03-10', 4, 'emp666'),
    (7, 'Jack Lee', 'Customer Service', '555-7777', 'jack.lee@email.com', '2023-05-01', 1, 'emp777'),
    (8, 'Karen Walker', 'Customer Service', '555-8888', 'karen.walker@email.com', '2023-07-15', 1, 'emp888'),
    (9, 'Lucas Hall', 'Procurement Specialist', '555-9999', 'lucas.hall@email.com', '2022-12-01', 1, 'emp999'),
    (10, 'Mia Scott', 'Procurement Specialist', '555-1010', 'mia.scott@email.com', '2023-02-05', 1, 'emp101'),
    (11, 'Noah Green', 'Inventory Specialist', '555-1212', 'noah.green@email.com', '2023-04-18', 4, 'emp121'),
    (12, 'Olivia King', 'Customer Service', '555-1313', 'olivia.king@email.com', '2023-06-22', 1, 'emp131'),
    (13, 'Peter White', 'Procurement Specialist', '555-1414', 'peter.white@email.com', '2022-11-10', 1, 'emp141'),
    (14, 'Quinn Baker', 'Customer Service', '555-1515', 'quinn.baker@email.com', '2023-08-30', 1, 'emp151'),
    (15, 'Rachel Young', 'Inventory Specialist', '555-1616', 'rachel.young@email.com', '2023-09-05', 4, 'emp161');-- 

INSERT INTO HourlyEmployee (employee_id, hours_worked, hourly_wages)
VALUES
(2, 40, 15.00),
(5, 35, 14.50),
(6, 40, 18.00),
(7, 32, 13.75),
(8, 37, 15.25);

INSERT INTO Contract (contract_id, contract_start_date, contract_end_date, salary)
VALUES
(1001, '2023-01-01', '2023-12-31', 50000.00),
(1002, '2023-01-01', '2024-12-31', 65000.00),
(1003, '2023-01-01', '2024-06-30', 55000.00);


INSERT INTO ContractEmployee (employee_id, contract_id)
VALUES
(3, 1001),
(5, 1002),
(9, 1003);

INSERT INTO Product (product_id, product_name, category, price, stock_quantity, stock_arrival_date)
VALUES
(1, 'Laptop', 'Electronics', 999.99, 25, '2024-03-09'),
(2, 'Smartphone', 'Electronics', 599.99, 50, '2024-02-10'),
(3, 'Headphones', 'Accessories', 129.99, 100, '2024-01-25'),
(4, 'Smartwatch', 'Accessories', 199.99, 75, '2024-02-01'),
(9, 'mic', 'Electronics', 99.99, 50, '2024-03-01'),
(6, 'mouse', 'Accessories', 199.99, 150, '2024-02-10');


INSERT INTO Supplier (supplier_id, supplier_name, email_address, phone_number)
VALUES
(1, 'Tech Supplies Co.', 'supplier1@email.com', '555-0001'),
(2, 'Gadget Distributors', 'supplier2@email.com', '555-0002');

INSERT INTO PurchaseOrder (purchase_order_id, employee_id, supplier_id, order_date, expected_received_date, actual_received_date)
VALUES
(1, 1, 1, '2024-03-15', '2024-03-25', '2024-03-24'),
(2, 2, 2, '2024-03-18', '2024-03-28', '2024-03-27');

INSERT INTO PurchaseOrderDetails ( purchase_order_id, product_id, price, quantity)
VALUES
( 1, 1, 999.99, 20),
(1, 2, 599.99, 30),
( 2, 3, 129.99, 50);


INSERT INTO Customer (customer_id, customer_name, phone_number, email_address, city, shipping_address, order_count, Customer_password) 
VALUES 
(4, 'Diana Miller', '555-9876', 'diana.miller@email.com', 'Houston', '321 Maple Ave, Houston, TX', 2, 'pass123'),
(5, 'Edward Wilson', '555-4321', 'edward.wilson@email.com', 'Phoenix', '654 Cedar Rd, Phoenix, AZ', 1, 'secure456'),
(6, 'Fiona Taylor', '555-6789', 'fiona.taylor@email.com', 'Philadelphia', '987 Birch Ln, Philadelphia, PA', 4, 'mypass789'),
(7, 'George Anderson', '555-1357', 'george.anderson@email.com', 'San Antonio', '147 Walnut St, San Antonio, TX', 6, 'password321'),
(8, 'Hannah White', '555-2468', 'hannah.white@email.com', 'San Diego', '258 Spruce Dr, San Diego, CA', 3, 'pass987'),
(9, 'Ivan Martinez', '555-3691', 'ivan.martinez@email.com', 'Dallas', '369 Poplar Blvd, Dallas, TX', 8, 'secure654'),
(10, 'Julia Garcia', '555-7410', 'julia.garcia@email.com', 'San Jose', '741 Ash Way, San Jose, CA', 2, 'mypass147');


INSERT INTO Product (product_id, product_name, category, price, stock_quantity, stock_arrival_date)
VALUES
(5, 'Tablet', 'Electronics', 349.99, 40, '2023-01-30'),
(7, 'Wireless Keyboard', 'Accessories', 79.99, 85, '2023-02-20'),
(8, 'Gaming Monitor', 'Electronics', 299.99, 30, '2022-03-05'),
(10, 'USB-C Cable', 'Accessories', 19.99, 200, '2022-01-15'),
(11, 'Webcam', 'Electronics', 89.99, 60, '2021-02-25'),
(12, 'Power Bank', 'Accessories', 49.99, 120, '2022-01-20'),
(13, 'Bluetooth Speaker', 'Electronics', 159.99, 45, '2020-03-10'),
(14, 'Phone Case', 'Accessories', 24.99, 180, '2020-02-05'),
(15, 'Laptop Stand', 'Accessories', 39.99, 70, '2020-01-18'),
(16, 'External Hard Drive', 'Electronics', 129.99, 55, '2021-02-28');

INSERT INTO `Order` (order_id, customer_id, employee_id, order_date, expected_received_date, actual_received_date)
VALUES
(1, 1, 2, '2023-12-15', '2023-12-20', '2023-12-22'),
(2, 2, 3, '2024-01-10', '2024-01-15', '2024-01-14'),
(3, 3, 5, '2024-03-05', '2024-03-10', '2024-03-09'),
(4, 4, 2, '2024-03-20', '2024-03-25', NULL),
(5, 5, 8, '2024-05-10', '2024-05-15', '2024-05-14'),
(6, 6, 3, '2024-05-15', '2024-05-20', '2024-05-25'), 
(7, 7, 5, '2025-06-01', '2025-06-06', NULL),
(8, 8, 2, '2025-06-03', '2025-06-08', NULL),
(9, 9, 8, '2025-06-04', '2025-06-09', NULL),
(10, 10, 3, '2025-06-06', '2025-06-11', NULL);



INSERT INTO OrderDetails ( order_id, product_id, price, quantity)
VALUES
(1, 1, 999.99, 1),
(1, 3, 129.99, 2),
(2, 2, 599.99, 1),
(3, 5, 349.99, 1),
(3, 12, 49.99, 2),
-- Order 4
(4, 8, 299.99, 1),
(4, 7, 79.99, 1),
(4, 5, 349.99, 1),
-- Order 5
(5, 11, 89.99, 1),
(5, 10, 19.99, 1),
(5, 15, 39.99, 1),
(5, 14, 24.99, 1),
-- Order 6 
(6, 13, 159.99, 2),
(6, 16, 129.99, 2),
-- Order 7
(7, 2, 599.99, 1),
(7, 8, 299.99, 1),
-- Order 8
(8, 14, 24.99, 5),
(8, 10, 19.99, 5),
(8, 12, 49.99, 1),
-- Order 9
(9, 7, 79.99, 2),
(9, 11, 89.99, 1),
(9, 13, 159.99, 1),
-- Order 10
(10, 15, 39.99, 2),
(10, 16, 129.99, 1);

INSERT INTO Invoice (invoice_id, order_id, invoice_date)
VALUES
(1, 1, '2024-04-04'),
(2, 2, '2024-04-05');

INSERT INTO Payment (payment_id, invoice_id, payment_date, amount_paid, payment_method)
VALUES
(1, 1, '2024-04-04', 1599.97, 'Credit Card'),
(2, 2, '2024-04-05', 599.99, 'PayPal');

INSERT INTO Supplier (supplier_id, supplier_name, email_address, phone_number)
VALUES
(3, 'ElectroSource Inc.', 'supplier3@email.com', '555-0003'),
(4, 'Digital Wholesale', 'supplier4@email.com', '555-0004'),
(5, 'Component Central', 'supplier5@email.com', '555-0005'),
(6, 'AccessoryHub', 'supplier6@email.com', '555-0006');

INSERT INTO PurchaseOrder (purchase_order_id, employee_id, supplier_id, order_date, expected_received_date, actual_received_date, delivery_status)
VALUES
(3, 9, 3, '2024-03-20', '2024-03-30', '2024-03-29', 'Received'),
(4, 6, 4, '2024-03-22', '2024-04-01', NULL, 'Shipped'),
(5, 9, 5, '2024-03-25', '2024-04-05', NULL, 'Pending'),
(6, 6, 6, '2024-03-28', '2024-04-08', NULL, 'Pending');

INSERT INTO PurchaseOrderDetails (purchase_order_id, product_id, price, quantity)
VALUES
-- Purchase Order 3
(3, 5, 349.99, 30),
(3, 11, 89.99, 40),
(3, 13, 159.99, 25),
-- Purchase Order 4
(4, 8, 299.99, 20),
(4, 7, 79.99, 60),
(4, 16, 129.99, 35),
-- Purchase Order 5
(5, 10, 19.99, 100),
(5, 12, 49.99, 80),
(5, 14, 24.99, 150),
-- Purchase Order 6
(6, 15, 39.99, 50),
(6, 6, 199.99, 20); 

INSERT INTO Invoice (invoice_id, order_id, invoice_date)
VALUES
(3, 3, '2024-04-06'),
(4, 4, '2024-04-04'),
(5, 5, '2024-04-05'),
(6, 6, '2024-04-06'),
(7, 7, '2024-04-07');

INSERT INTO Payment (payment_id, invoice_id, payment_date, amount_paid, payment_method)
VALUES
(3, 3, '2024-04-06', 449.98, 'Debit Card'),
(4, 4, '2024-04-04', 729.97, 'Credit Card'),
(5, 5, '2024-04-05', 179.98, 'PayPal'),
(6, 6, '2024-04-06', 299.98, 'Credit Card'), -- Partial payment
(7, 7, '2024-04-07', 889.95, 'Bank Transfer');
