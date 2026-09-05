import os
from functools import wraps
from decimal import Decimal, InvalidOperation

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    'SECRET_KEY',
    'replace_this_with_a_random_secret'
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', ''),
    'database': os.getenv('DB_NAME', 'online_banking'),
    'port': int(os.getenv('DB_PORT', '3306'))
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# HELPER: CLOSE DATABASE RESOURCES
# ============================================================

def close_db(conn=None, cur=None):
    try:
        if cur is not None:
            cur.close()
    except Exception:
        pass

    try:
        if conn is not None:
            conn.close()
    except Exception:
        pass


# ============================================================
# HELPER: VALIDATE MONEY AMOUNT
# ============================================================

def get_amount(value):
    """
    Convert a form amount into Decimal.

    Returns:
        Decimal amount if valid
        None if invalid
    """

    if value is None:
        return None

    try:
        amount = Decimal(str(value))

        if amount <= 0:
            return None

        # Prevent excessively precise monetary values
        amount = amount.quantize(Decimal('0.01'))

        return amount

    except (InvalidOperation, ValueError, TypeError):
        return None


# ============================================================
# HOME
# ============================================================

@app.route('/')
def index():
    return redirect(url_for('login'))


# ============================================================
# SEED ADMIN
# ============================================================

@app.route('/setup_seed_admin')
def setup_seed_admin():
    seed_id = os.getenv('SEED_ADMIN_ID', '007')
    seed_pw = os.getenv('SEED_ADMIN_PASS', 'emp@123')

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        hashed = generate_password_hash(seed_pw)

        cur.execute(
            """
            UPDATE employees
            SET password_hash=%s
            WHERE emp_number=%s
            """,
            (hashed, seed_id)
        )

        conn.commit()

        return 'Seeded admin successfully (ID: {})'.format(seed_id)

    except Exception as e:
        return 'Error seeding admin: ' + str(e), 500

    finally:
        close_db(conn, cur)


# ============================================================
# LOGIN
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        userid = request.form.get('userid', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')

        if not userid or not password:
            flash('Please enter your ID and password.')
            return render_template('login.html')

        conn = None
        cur = None

        try:
            conn = get_db_connection()
            cur = conn.cursor(dictionary=True)

            # ------------------------------------------------
            # EMPLOYEE LOGIN
            # ------------------------------------------------

            if role == 'employee':

                cur.execute(
                    """
                    SELECT *
                    FROM employees
                    WHERE emp_number=%s
                    """,
                    (userid,)
                )

                row = cur.fetchone()

                if (
                    row
                    and row.get('password_hash')
                    and check_password_hash(
                        row['password_hash'],
                        password
                    )
                ):
                    session.clear()

                    session['emp'] = row['emp_number']
                    session['emp_name'] = row.get('name', '')

                    return redirect(
                        url_for('employee_dashboard')
                    )

                flash('Invalid employee credentials.')

            # ------------------------------------------------
            # USER LOGIN
            # ------------------------------------------------

            else:

                cur.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE account_number=%s
                    """,
                    (userid,)
                )

                row = cur.fetchone()

                if (
                    row
                    and row.get('password_hash')
                    and check_password_hash(
                        row['password_hash'],
                        password
                    )
                ):
                    session.clear()

                    session['user'] = row['account_number']
                    session['user_name'] = row.get('name', '')

                    return redirect(
                        url_for('user_dashboard')
                    )

                flash('Invalid user credentials.')

        except Exception as e:
            flash('DB error: ' + str(e))

        finally:
            close_db(conn, cur)

    return render_template('login.html')


# ============================================================
# LOGOUT
# ============================================================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ============================================================
# EMPLOYEE AUTHENTICATION DECORATOR
# ============================================================

def emp_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if 'emp' not in session:
            flash('Please login as employee.')
            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return wrapper


# ============================================================
# EMPLOYEE DASHBOARD
# ============================================================

@app.route('/employee')
@emp_required
def employee_dashboard():

    conn = None
    cur = None

    stats = {
        'total_users': 0,
        'total_balance': Decimal('0.00')
    }

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """
            SELECT
                COUNT(*) AS total_users,
                COALESCE(SUM(balance), 0) AS total_balance
            FROM users
            """
        )

        result = cur.fetchone()

        if result:
            stats = result

    except Exception as e:
        flash('Error loading dashboard: ' + str(e))

    finally:
        close_db(conn, cur)

    return render_template(
        'employee_dashboard.html',
        stats=stats
    )


# ============================================================
# CREATE USER
# ============================================================

@app.route('/employee/create_user', methods=['POST'])
@emp_required
def create_user():

    acc = request.form.get('account_number', '').strip()
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '')

    if not acc or not name or not password:
        flash('Account number, name and password are required.')
        return redirect(url_for('employee_dashboard'))

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        hashed = generate_password_hash(password)

        cur.execute(
            """
            INSERT INTO users
                (account_number, name, password_hash, balance)
            VALUES
                (%s, %s, %s, %s)
            """,
            (
                acc,
                name,
                hashed,
                Decimal('0.00')
            )
        )

        conn.commit()

        flash('User created: ' + str(acc))

    except mysql.connector.IntegrityError:
        if conn:
            conn.rollback()

        flash(
            'Error creating user: '
            'Account number may already exist.'
        )

    except Exception as e:
        if conn:
            conn.rollback()

        flash('Error creating user: ' + str(e))

    finally:
        close_db(conn, cur)

    return redirect(url_for('employee_dashboard'))


# ============================================================
# SET FD
# ============================================================

@app.route('/employee/set_fd', methods=['POST'])
@emp_required
def set_fd():

    acc = request.form.get('account_number', '').strip()
    amount_value = request.form.get('amount')
    remark = request.form.get(
        'remark',
        'FD set by employee'
    ).strip()

    amount = get_amount(amount_value)

    if not acc:
        flash('Account number is required.')
        return redirect(url_for('employee_dashboard'))

    if amount is None:
        flash('Please enter a valid FD amount.')
        return redirect(url_for('employee_dashboard'))

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Make sure account exists
        cur.execute(
            """
            SELECT account_number
            FROM users
            WHERE account_number=%s
            """,
            (acc,)
        )

        user = cur.fetchone()

        if not user:
            flash('User account not found.')
            return redirect(url_for('employee_dashboard'))

        cur.execute(
            """
            UPDATE users
            SET fd_amount=%s
            WHERE account_number=%s
            """,
            (amount, acc)
        )

        cur.execute(
            """
            INSERT INTO transactions
                (account_number, type, amount, remark)
            VALUES
                (%s, %s, %s, %s)
            """,
            (
                acc,
                'fd_open',
                amount,
                remark
            )
        )

        conn.commit()

        flash('FD set for ' + str(acc))

    except Exception as e:
        if conn:
            conn.rollback()

        flash('Error setting FD: ' + str(e))

    finally:
        close_db(conn, cur)

    return redirect(url_for('employee_dashboard'))


# ============================================================
# SET LOAN
# ============================================================

@app.route('/employee/set_loan', methods=['POST'])
@emp_required
def set_loan():

    acc = request.form.get('account_number', '').strip()
    amount_value = request.form.get('amount')
    remark = request.form.get(
        'remark',
        'Loan set by employee'
    ).strip()

    amount = get_amount(amount_value)

    if not acc:
        flash('Account number is required.')
        return redirect(url_for('employee_dashboard'))

    if amount is None:
        flash('Please enter a valid loan amount.')
        return redirect(url_for('employee_dashboard'))

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check account
        cur.execute(
            """
            SELECT account_number
            FROM users
            WHERE account_number=%s
            """,
            (acc,)
        )

        user = cur.fetchone()

        if not user:
            flash('User account not found.')
            return redirect(url_for('employee_dashboard'))

        # Update loan amount
        cur.execute(
            """
            UPDATE users
            SET loan_amount=%s
            WHERE account_number=%s
            """,
            (amount, acc)
        )

        # Add loan amount to balance
        cur.execute(
            """
            UPDATE users
            SET balance = balance + %s
            WHERE account_number=%s
            """,
            (amount, acc)
        )

        # Add transaction
        cur.execute(
            """
            INSERT INTO transactions
                (account_number, type, amount, remark)
            VALUES
                (%s, %s, %s, %s)
            """,
            (
                acc,
                'loan_disburse',
                amount,
                remark
            )
        )

        conn.commit()

        flash('Loan disbursed to ' + str(acc))

    except Exception as e:
        if conn:
            conn.rollback()

        flash('Error setting loan: ' + str(e))

    finally:
        close_db(conn, cur)

    return redirect(url_for('employee_dashboard'))


# ============================================================
# EMPLOYEE TRANSACTIONS
# ============================================================

@app.route('/employee/transactions', methods=['GET'])
@emp_required
def employee_transactions():

    q = request.args.get('q', '').strip()

    conn = None
    cur = None

    # IMPORTANT:
    # employee_transactions.html expects "stats"
    stats = {
        'total_users': 0,
        'total_balance': Decimal('0.00')
    }

    txs = []

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # ------------------------------------------------
        # GET STATISTICS
        # ------------------------------------------------

        cur.execute(
            """
            SELECT
                COUNT(*) AS total_users,
                COALESCE(SUM(balance), 0) AS total_balance
            FROM users
            """
        )

        stats_result = cur.fetchone()

        if stats_result:
            stats = stats_result

        # ------------------------------------------------
        # GET TRANSACTIONS
        # ------------------------------------------------

        if q:

            cur.execute(
                """
                SELECT *
                FROM transactions
                WHERE account_number=%s
                ORDER BY date DESC
                LIMIT 100
                """,
                (q,)
            )

        else:

            cur.execute(
                """
                SELECT *
                FROM transactions
                ORDER BY date DESC
                LIMIT 200
                """
            )

        txs = cur.fetchall()

    except Exception as e:

        flash(
            'Error fetching transactions: '
            + str(e)
        )

    finally:
        close_db(conn, cur)

    # IMPORTANT:
    # stats is now passed to the template.
    return render_template(
        'employee_transactions.html',
        txs=txs,
        query=q,
        stats=stats
    )


# ============================================================
# USER AUTHENTICATION DECORATOR
# ============================================================

def user_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if 'user' not in session:
            flash('Please login as user.')
            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return wrapper


# ============================================================
# USER DASHBOARD
# ============================================================

@app.route('/user', methods=['GET'])
@user_required
def user_dashboard():

    acc = session.get('user')

    conn = None
    cur = None

    user = None
    txs = []

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Get user information
        cur.execute(
            """
            SELECT
                account_number,
                name,
                balance,
                fd_amount,
                loan_amount
            FROM users
            WHERE account_number=%s
            """,
            (acc,)
        )

        user = cur.fetchone()

        # Get recent transactions
        cur.execute(
            """
            SELECT *
            FROM transactions
            WHERE account_number=%s
            ORDER BY date DESC
            LIMIT 10
            """,
            (acc,)
        )

        txs = cur.fetchall()

    except Exception as e:

        flash('Error: ' + str(e))

    finally:
        close_db(conn, cur)

    return render_template(
        'user_dashboard.html',
        user=user,
        txs=txs
    )


# ============================================================
# DEPOSIT
# ============================================================

@app.route('/deposit', methods=['POST'])
@user_required
def deposit():

    acc = session.get('user')

    amount_value = request.form.get('amount')

    remark = request.form.get(
        'remark',
        'Deposit by user'
    ).strip()

    amount = get_amount(amount_value)

    if amount is None:
        flash('Please enter a valid deposit amount.')
        return redirect(url_for('user_dashboard'))

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Update balance
        cur.execute(
            """
            UPDATE users
            SET balance = balance + %s
            WHERE account_number=%s
            """,
            (amount, acc)
        )

        if cur.rowcount == 0:
            conn.rollback()
            flash('User account not found.')
            return redirect(url_for('user_dashboard'))

        # Record transaction
        cur.execute(
            """
            INSERT INTO transactions
                (account_number, type, amount, remark)
            VALUES
                (%s, %s, %s, %s)
            """,
            (
                acc,
                'deposit',
                amount,
                remark
            )
        )

        conn.commit()

        flash('Deposit successful.')

    except Exception as e:

        if conn:
            conn.rollback()

        flash('Error depositing: ' + str(e))

    finally:
        close_db(conn, cur)

    return redirect(url_for('user_dashboard'))


# ============================================================
# WITHDRAW
# ============================================================

@app.route('/withdraw', methods=['POST'])
@user_required
def withdraw():

    acc = session.get('user')

    amount_value = request.form.get('amount')

    remark = request.form.get(
        'remark',
        'Withdraw by user'
    ).strip()

    amount = get_amount(amount_value)

    if amount is None:
        flash('Please enter a valid withdrawal amount.')
        return redirect(url_for('user_dashboard'))

    conn = None
    cur = None

    try:
        conn = get_db_connection()

        # Use one cursor
        cur = conn.cursor(dictionary=True)

        # Check current balance
        cur.execute(
            """
            SELECT balance
            FROM users
            WHERE account_number=%s
            """,
            (acc,)
        )

        row = cur.fetchone()

        if not row:
            flash('User account not found.')
            return redirect(url_for('user_dashboard'))

        balance = Decimal(str(row.get('balance') or 0))

        if balance < amount:
            flash('Insufficient balance.')
            return redirect(url_for('user_dashboard'))

        # Switch to regular cursor for UPDATE/INSERT
        cur.close()

        cur = conn.cursor()

        # Withdraw
        cur.execute(
            """
            UPDATE users
            SET balance = balance - %s
            WHERE account_number=%s
            """,
            (amount, acc)
        )

        # Record transaction
        cur.execute(
            """
            INSERT INTO transactions
                (account_number, type, amount, remark)
            VALUES
                (%s, %s, %s, %s)
            """,
            (
                acc,
                'withdraw',
                amount,
                remark
            )
        )

        conn.commit()

        flash('Withdrawal successful.')

    except Exception as e:

        if conn:
            conn.rollback()

        flash('Error withdrawing: ' + str(e))

    finally:
        close_db(conn, cur)

    return redirect(url_for('user_dashboard'))


# ============================================================
# API: ACCOUNT LOOKUP
# ============================================================

@app.route('/api/account/<acct>')
@emp_required
def api_account(acct):

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            """
            SELECT
                account_number,
                name,
                balance,
                fd_amount,
                loan_amount
            FROM users
            WHERE account_number=%s
            """,
            (acct,)
        )

        row = cur.fetchone()

        if not row:
            return jsonify({
                'error': 'not found'
            }), 404

        return jsonify(row)

    except Exception as e:

        return jsonify({
            'error': str(e)
        }), 500

    finally:
        close_db(conn, cur)


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == '__main__':

    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000
    )
