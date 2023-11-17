CREATE TABLE Customer (
	customer_id INT PRIMARY KEY,
	first_name VARCHAR(50),
	middle_name VARCHAR(50),
	father_last_name VARCHAR(50),
	mother_last_name VARCHAR(50),
	phone_number INT,
	curp VARCHAR(20),
	customer_rfc VARCHAR(15),
	address VARCHAR(100)
);

CREATE TABLE Items (
	item_id INT PRIMARY KEY,
	item_name VARCHAR(50),
	current_price VARCHAR(50)
);

CREATE TABLE Store (
	sotore_id INT PRIMARY KEY,
	store_name VARCHAR(50),
	cordinates VARCHAR(50)
);