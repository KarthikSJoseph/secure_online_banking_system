CREATE DATABASE IF NOT EXISTS online_banking;
USE online_banking;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_number BIGINT UNIQUE NOT NULL,
    name VARCHAR(100),
    password_hash VARCHAR(255),
    balance DECIMAL(15,2) DEFAULT 0.00,
    fd_amount DECIMAL(15,2) DEFAULT 0.00,
    loan_amount DECIMAL(15,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    emp_number VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(100),
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_number BIGINT,
    type ENUM('deposit','withdraw','fd_open','loan_disburse','fd_mature','loan_repay') NOT NULL,
    amount DECIMAL(15,2),
    remark VARCHAR(255),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional: insert a placeholder employee row. Password will be seeded by the app.
INSERT INTO employees (emp_number, name, password_hash) VALUES ('007', 'Admin', 'TO_BE_HASHED')
ON DUPLICATE KEY UPDATE name=VALUES(name);
