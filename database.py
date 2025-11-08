import sqlite3
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor

# Use the environment variable for the DB path if it exists, otherwise default to a local file.
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Creates a database connection. The connection object can access columns by name."""
    if DATABASE_URL: # Production environment on Render
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
    else: # Local development environment
        conn = sqlite3.connect('outercircle.db')
        conn.row_factory = sqlite3.Row
    return conn

def init_db(force_recreate=False):
    """Initializes the database and creates tables if they don't exist."""
    # Local DB recreation logic
    if not DATABASE_URL and force_recreate and os.path.exists('outercircle.db'):
        os.remove('outercircle.db')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create a 'users' table to store the unique codes.
    # This ensures a user code is a persistent entity.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            code TEXT PRIMARY KEY NOT NULL
        )
    ''')

    # Create a 'messages' table with a foreign key relationship to the 'users' table.
    # This links each message to a specific user code.
    # Use SERIAL for auto-incrementing ID in PostgreSQL
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_code TEXT NOT NULL,
            message TEXT NOT NULL,
            sensitivity TEXT,
            delivery TEXT,
            timestamp_utc TEXT NOT NULL,
            FOREIGN KEY (user_code) REFERENCES users (code)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized.")

def code_exists(code):
    """Checks if a user code exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT code FROM users WHERE code = %s', (code,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user is not None

def create_user(code):
    """Adds a new user code to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (code) VALUES (%s)', (code,))
    cursor.close()
    conn.commit()
    conn.close()

def add_message_for_code(code, message_data):
    """Adds a new message for a given user code."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO messages (user_code, message, sensitivity, delivery, timestamp_utc) VALUES (%s, %s, %s, %s, %s)',
        (code, message_data['message'], message_data['sensitivity'], message_data['delivery'], message_data['timestamp_utc'])
    )
    cursor.close()
    conn.commit()
    conn.close()

def get_all_messages_grouped():
    """Retrieves all messages, grouped by user code, for the admin view."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages ORDER BY user_code, timestamp_utc DESC')
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return messages