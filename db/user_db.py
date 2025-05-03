import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Database file path
DATABASE = 'users.db'

# Establishes a connection to the database and configures row factory
def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enables dict-like access to row data
    return conn

# Creates the users table if it does not exist
def create_users_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Adds a new user to the database
# Returns True if successful, False if the username already exists (UNIQUE constraint)
def add_user(username, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)  
        )

        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# Retrieves user information by username (used for login)
def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

# Retrieves user information by user ID (used by session manager)
def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
