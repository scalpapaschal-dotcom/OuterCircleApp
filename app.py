import secrets
import string
import os
import json
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Needed for session management

# --- Configuration ---
CODE_LENGTH = 4
CODE_CHARS = string.ascii_uppercase + string.digits
DB_FILE = 'user_messages.json'

# --- "Database" Functions ---

def load_messages_db(): #The name of the file used to store all codes and their associated messages.
    """Loads the message database (a dictionary of codes to messages) from a JSON file."""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, 'r') as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        print(f"Warning: Could not read or parse {DB_FILE}. Starting with an empty database.")
        return {}

def save_messages_db(db):
    """Saves the message database to a JSON file."""
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

# --- Core Logic ---

def generate_unique_code(existing_codes): #It runs in a loop to ensure the generated code is unique (not already a key in the existing database).
    """Generates a unique code that is not already in use."""
    while True:
        new_code = ''.join(secrets.choice(CODE_CHARS) for _ in range(CODE_LENGTH))
        if new_code not in existing_codes:
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
    db = load_messages_db()
    user_code = generate_unique_code(db.keys())
    db[user_code] = []
    save_messages_db(db)
    return render_template('OuterCircleCode.html', code=user_code)

@app.route('/login', methods=['POST'])
def login():
    """Validates an existing user code and shows the message submission page."""
    db = load_messages_db()
    code = request.form.get('user-code', '').upper()

    if code and code in db:
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
    db = load_messages_db()
    
    # Get data from the submitted form
    code = request.form.get('user-code', '').upper()
    message = request.form.get('message') or request.form.get('anon-message')
    sensitivity = request.form.get('sensitivity')
    delivery = request.form.get('delivery')

    # Basic validation
    if not code or code not in db:
        return render_template('Error.html'), 400
    if not message:
        return "Error: Message cannot be empty.", 400

    # Create a message object
    new_message = {
        "message": message,
        "sensitivity": sensitivity,
        "delivery": delivery,
        "timestamp_utc": datetime.utcnow().isoformat()
    }
    # Add the message to the user's record and save
    db[code].append(new_message)
    save_messages_db(db)

    # Render the encouragement page, passing the user's code back.
    return render_template('EncouragementPage.html', code=code)

@app.route('/messages')
def view_messages():
    """
    Admin-facing page to view all submitted messages.
    NOTE: In a production environment, this route should be protected
    with authentication and authorization.
    """
    messages_db = load_messages_db()
    # Render the admin view, passing the entire database to the template.
    return render_template('admin_view.html', messages_db=messages_db)

if __name__ == '__main__':
    # The 'debug=True' part is for development; remove it for production.
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True)
