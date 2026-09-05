ONLINE BANKING - QUICK START (Windows / macOS / Linux)
----------------------------------------------------

Prerequisites:
- Python 3.11 installed
- MySQL Server running (you said localhost:3306) and MySQL Workbench available
- The project's MySQL credentials are set to root / root by default in the .env file

Steps:

1) Unzip the package into a folder, open a terminal in that folder.

2) Create & activate a Python virtual environment:
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS / Linux:
   source venv/bin/activate

3) Install Python dependencies:
   pip install -r requirements.txt

4) Open MySQL Workbench and run the SQL script:
   - Open a new SQL tab, paste the content of init_db.sql and execute it.
   - This creates the `online_banking` database and the required tables.

5) (Seed admin password)
   - Start the Flask app:
       python app.py
   - In your browser visit:
       http://127.0.0.1:5000/setup_seed_admin
     This will hash and save the admin password stored in the .env file (SEED_ADMIN_ID / SEED_ADMIN_PASS).
     You should see a 'Seeded admin' confirmation.

6) Login:
   - Go to: http://127.0.0.1:5000/login
   - Employee login:
       ID: 007
       Password: emp@123
     (Choose the Employee role)
   - Create user accounts from Employee dashboard.

7) Typical flow:
   - Employee creates a user with an account number and password.
   - User logs in, deposits/withdraws, and sees transactions.

Notes:
- For production, configure SECRET_KEY and never run with debug=True.
- This project uses MySQL Connector (pure Python) to avoid system-specific compilation.
