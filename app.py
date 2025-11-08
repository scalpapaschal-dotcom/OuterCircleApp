import secrets
import string
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import database as db # Import our new database module

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Needed for session management

# Initialize the database when the app module is first imported.
db.init_db()

# --- Configuration ---
CODE_LENGTH = 4
CODE_CHARS = string.ascii_uppercase + string.digits
# IMPORTANT: For a real application, store this password securely as an environment variable.
# For example: ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'default_password')
ADMIN_PASSWORD = "SAVE" # You can change "SAVE" to any password you like.

# --- Core Logic ---

def generate_unique_code(): #It runs in a loop to ensure the generated code is unique (not already a key in the existing database).
    """Generates a unique code that is not already in use."""
    while True:
        new_code = ''.join(secrets.choice(CODE_CHARS) for _ in range(CODE_LENGTH))
        if not db.code_exists(new_code):
            return new_code

# --- Flask Routes (Web Pages) ---

@app.route('/')
def home():
    """Renders the start page where users can choose to get a new code or use an existing one."""
    return render_template('start.html')

@app.route('/new-code')
def new_code():
    """
    Generates a new code for a new user and shows the message submission page.
    """
    user_code = generate_unique_code()
    with db.get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('INSERT INTO users (code) VALUES (%s)', (user_code,))
    
    return render_template('OuterCircleCode.html', code=user_code)

@app.route('/login', methods=['POST'])
def login():
    """Validates an existing user code and shows the message submission page."""
    code = request.form.get('user-code', '').upper()

    if code and db.code_exists(code):
        # If code is valid, show the submission page
        return render_template('OuterCircleCode.html', code=code)
    else:
        # If code is invalid, show the start page again with an error
        return render_template('start.html', error="Invalid code. Please try again or get a new one.")

@app.route('/submit-message', methods=['POST'])
def submit_message():
    """
    Handles the form submission.
    """
    # Get data from the submitted form
    code = request.form.get('user-code', '').upper()
    message_text = request.form.get('anon-message')
    sensitivity = request.form.get('sensitivity')
    delivery = request.form.get('delivery')

    # Basic validation
    # Check if the code exists in our new database
    if not code or not db.code_exists(code):
        return render_template('Error.html'), 400
    if not message_text:
        return "Error: Message cannot be empty.", 400

    # Create a message object
    new_message = {
        "message": message_text,
        "sensitivity": sensitivity,
        "delivery": delivery,
        "timestamp_utc": datetime.utcnow().isoformat()
    }

    # Add the message to the database
    with db.get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO messages (user_code, message, sensitivity, delivery, timestamp_utc) VALUES (%s, %s, %s, %s, %s)',
                (code, new_message['message'], new_message['sensitivity'], new_message['delivery'], new_message['timestamp_utc'])
            )
    # Render the encouragement page, passing the user's code back.
    return render_template('EncouragementPage.html', code=code)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    """Handles the admin login process."""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('view_messages'))
        else:
            flash('Incorrect password.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Logs the admin out."""
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/messages')
def view_messages():
    """
    Admin-facing page to view all submitted messages.
    This route is now protected and requires login.
    """
    # Check if the admin is logged in
    if not session.get('admin_logged_in'):
        # If not logged in, redirect to the admin login page
        return redirect(url_for('admin_login'))

    # If logged in, proceed to show the messages
    all_messages = db.get_all_messages_grouped()
    return render_template('admin_view.html', messages=all_messages)

if __name__ == '__main__':
    # Initialize the database when the app starts
    app.run(debug=True) # Use debug mode for local development
