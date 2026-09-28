# Secure Online Banking System

A role-based online banking web application built with Flask and MySQL. Bank employees create and manage customer accounts; customers log in to view their balance, deposit and withdraw money, and see their transaction history.

## Features

**Customer**
- Log in with account number and password
- Dashboard with balance, fixed deposit (FD) amount, loan amount and recent transactions
- Deposit and withdraw money

**Employee**
- Log in with employee ID and password
- Create customer accounts (password stored hashed)
- Set an FD amount or a loan amount on an account (recorded as transactions)
- Dashboard with total customers and total balance
- View the full transaction log
- Look up an account by number (`/api/account/<acct>`, JSON)

## Tech stack

| Area | Technology |
|---|---|
| Backend | Python 3.11, Flask |
| Database | MySQL (`mysql-connector-python`) |
| Security | Werkzeug password hashing, Flask sessions, `python-dotenv` for configuration |
| Frontend | Jinja2 templates, HTML, CSS |

## Security measures implemented

- Passwords are stored only as salted hashes (`generate_password_hash` / `check_password_hash`).
- All SQL uses **parameterized queries**, so user input is never concatenated into SQL.
- Separate session keys and decorators for customers (`user_required`) and employees (`emp_required`) enforce role-based access to routes.
- The session is cleared on login and logout.
- Money is handled with Python `Decimal` and `DECIMAL(15,2)` columns, not floats; amounts must be positive and are rounded to two decimals.
- Each write operation commits explicitly and rolls back on error.
- Secrets and database credentials are read from environment variables; `.env` is git-ignored.

## Database schema

Defined in `init_db.sql`:

| Table | Key columns |
|---|---|
| `users` | `account_number` (unique), `name`, `password_hash`, `balance`, `fd_amount`, `loan_amount`, `created_at` |
| `employees` | `emp_number` (unique), `name`, `password_hash`, `created_at` |
| `transactions` | `account_number`, `type` (`deposit`, `withdraw`, `fd_open`, `loan_disburse`, `fd_mature`, `loan_repay`), `amount`, `remark`, `date` |

## Project structure

```
├── app.py               # Routes, authentication, banking logic
├── init_db.sql          # Database and table creation
├── requirements.txt
├── templates/           # login, user_dashboard, employee_dashboard, employee_transactions
└── static/style.css
```

## Getting started

### Prerequisites
- Python 3.11
- MySQL Server (local or remote) and a client such as MySQL Workbench or the `mysql` CLI

### 1. Clone and install

```bash
git clone https://github.com/KarthikSJoseph/secure_online_banking_system.git
cd secure_online_banking_system

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create the database

Run `init_db.sql` in your MySQL client. This creates the `online_banking` database, the three tables and a placeholder employee row (`emp_number = 007`).

### 3. Configure environment variables

Create a `.env` file in the project root (it is git-ignored):

```env
SECRET_KEY=<long random string>
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=<mysql user>
DB_PASS=<mysql password>
DB_NAME=online_banking
SEED_ADMIN_ID=007
SEED_ADMIN_PASS=<choose a strong admin password>
```

Use a dedicated MySQL user with rights only on `online_banking`, rather than `root`.

### 4. Seed the admin password

```bash
python app.py
```

Then open `http://127.0.0.1:5000/setup_seed_admin` **once**. It hashes `SEED_ADMIN_PASS` and stores it for the employee `SEED_ADMIN_ID`.

### 5. Use the application

1. Go to `http://127.0.0.1:5000/login`, choose **Employee** and sign in with the seeded credentials.
2. Create a customer account from the employee dashboard.
3. Log out, then sign in as **User** with the new account number to deposit, withdraw and view transactions.

## Routes

| Route | Access | Purpose |
|---|---|---|
| `/login`, `/logout` | Public / any | Authentication |
| `/setup_seed_admin` | Public (one-time setup) | Set the seeded admin's password |
| `/employee` | Employee | Dashboard and statistics |
| `/employee/create_user` | Employee | Create a customer account |
| `/employee/set_fd`, `/employee/set_loan` | Employee | Record an FD or loan for an account |
| `/employee/transactions` | Employee | Full transaction log |
| `/api/account/<acct>` | Employee | Account details as JSON |
| `/user` | Customer | Dashboard and recent transactions |
| `/deposit`, `/withdraw` | Customer | Money operations |

## Known limitations

This is a learning project and is not production banking software. The current gaps are:

- **Withdrawal is not atomic.** The balance is read, checked in Python, then updated in a separate statement, so two simultaneous withdrawals could overdraw an account. The fix is a single conditional `UPDATE ... WHERE balance >= amount` (or `SELECT ... FOR UPDATE`).
- **FD and loan handling is simplified.** Setting an FD records the amount but does not deduct it from the balance; a loan overwrites `loan_amount` while adding to the balance. FD maturity and loan repayment types exist in the schema but are not implemented.
- **No CSRF protection** on form submissions (Flask-WTF `CSRFProtect` would add it) and **no login rate-limiting**.
- **`/setup_seed_admin` is an unauthenticated setup route.** Use it once during setup and remove or protect it afterwards.
- **Development settings.** `app.run(debug=True)` is for local use only; run behind Gunicorn with debug off in any shared environment. `SECRET_KEY` must be set in the environment, since a placeholder is used if it is missing.
- **Error messages.** Some database errors are shown to the user via flash messages; production code should log details and show a generic message.

## Future improvements

- Atomic balance updates and database transactions for all money movements
- Complete FD and loan lifecycle (open, mature, repay, interest)
- CSRF protection, rate limiting, account lockout and audit logging
- Automated tests and a production WSGI deployment

## Author

**Karthik S. Joseph** – B.Tech Computer Science and Engineering, SCMS College of Engineering and Technology
[GitHub](https://github.com/KarthikSJoseph) · [LinkedIn](https://linkedin.com/in/karthik-s-joseph)
