INSERT INTO customers VALUES
(1, 'Alice', 'Delhi', '2023-01-05'),
(2, 'Bob', 'Mumbai', '2023-03-12'),
(3, 'Charlie', 'Delhi', '2023-06-27'),
(4, 'Diana', 'Bangalore', '2023-07-21');

INSERT INTO products VALUES
(101, 'iPhone', 'Electronics', 80000),
(102, 'Headphones', 'Electronics', 5000),
(103, 'Shoes', 'Footwear', 3500),
(104, 'Notebook', 'Stationery', 120);

INSERT INTO orders VALUES
(1001, 1, '2023-04-15', 80000, 'delivered'),
(1002, 2, '2023-04-18', 88500, 'cancelled'),
(1003, 1, '2023-05-25', 5100, 'delivered'),
(1004, 3, '2023-07-02', 120, 'delivered'),
(1005, 2, '2023-08-11', 3850, 'pending');

INSERT INTO order_items VALUES
(1, 1001, 101, 1, 80000),
(2, 1002, 101, 1, 80000),
(3, 1002, 102, 1, 5000),
(4, 1003, 102, 1, 5000),
(5, 1004, 104, 1, 120),
(6, 1005, 103, 1, 3500),
(7, 1005, 104, 5, 350);





