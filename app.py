# -------------------------
# Imports & Configuration
# -------------------------

import os
import pickle
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from config import SECRET_KEY, SESSION_TYPE, SESSION_PERMANENT, CREDENTIALS_FILE, SCOPES, REDIRECT_URI

# Set environment variable to allow OAuth2 over HTTP (only for development)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Flask & extensions
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

# Database modules
import sqlite3
from db.task_db import TaskDB
from db.user_db import get_user_by_id, get_user_by_username, add_user, create_users_table
from utils.availability_manager import is_slot_free, mark_task_as_busy, initialize_availability

# Google Calendar utilities
from utils.google_calendar import (
    get_calendar_service,
    get_calendar_flow,
    save_credentials,
    create_event,
    get_upcoming_events,
    CREDENTIALS_FILE,
    SCOPES
)
from google_auth_oauthlib.flow import Flow

# Scheduling utilities
from utils.scheduler import find_time_slot
from utils.datetime_utils import convert_task_to_datetime

# ========================
# Flask App Initialization
# ========================

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = SESSION_TYPE
app.config['SESSION_PERMANENT'] = SESSION_PERMANENT

# Make session permanent before each request
@app.before_request
def make_session_permanent():
    session.permanent = True

# =====================
# Database Initialization
# =====================

db = TaskDB()  # Local SQLite handler for tasks
db.create_table()
create_users_table()  # Creates the users table if it doesn't exist

# ====================
# Flask-Login Setup
# ====================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect unauthenticated users to /login

# ========================
# User Class & User Loader
# ========================

class User(UserMixin):
    """Custom User class compatible with Flask-Login"""
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    """Fetch user by ID from the database and return as User instance"""
    user_data = get_user_by_id(user_id)
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['password'])
    return None

# ===========================
# Public and Protected Routes
# ===========================

@app.route("/")
def index():
    """Homepage route (public)"""
    return render_template("index.html")

@app.route("/about")
def about():
    """About page (public)"""
    return render_template("about.html")

@app.route("/contact")
def contact():
    """Contact page (public)"""
    return render_template("contact.html")

@app.route("/weekly-schedule")
@login_required
def weekly_schedule():
    """Displays the weekly schedule table (requires login)"""
    return render_template("weekly-schedule.html")

@app.route("/tasks")
@login_required
def tasks():
    print("[DEBUG] current_user.id =", current_user.id)
    """Displays the task list grouped by priority (requires login)"""
    list_task = db.get_list_of_tasks(current_user.id)
    return render_template("tasks.html", list_task=list_task)

@app.route("/api/tasks")
@login_required
def get_tasks_json():
    """
    JSON API endpoint for fetching user tasks.
    Accepts optional query params: day & time (used by the frontend modal)
    """
    day = request.args.get('day')
    time = request.args.get('time')
    try:
        if day and time:
            tasks_list = db.get_tasks_by_day_and_time(current_user.id, day, time)
        else:
            tasks_list = db.get_tasks_json(current_user.id)

        return jsonify({"success": True, "tasks": tasks_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user_data = get_user_by_username(username)
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'], user_data['username'], user_data['password'])
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password", "error")
    return render_template("login.html")
    
@app.route("/logout")
@login_required
def logout():
    """
    Logs out the current user and redirects to homepage.
    """
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles user registration.
    If username exists or invalid, shows error.
    On success, redirects to login page.
    """
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Check if user already exists
        if get_user_by_username(username):
            flash("Username already exists", "error")
        elif not add_user(username, password):
            flash("Could not create user", "error")
        else:
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")

# ================
# Helper Function
# ================
def get_next_day(current_day):
    """Returns the next day of the week given a current day."""
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_index = days_order.index(current_day)
    return days_order[(current_index + 1) % 7]


# ==============================
# Main Route for Adding a Task
# ==============================
@app.route("/add_task", methods=["POST"])
@login_required
def add_task():
    try:
        data = request.get_json()
        print("[DEBUG] Incoming data to /add_task:", data)

        if data.get("mode") == "auto":
            if data['deadline_day'] == "Monday" and data['deadline_time'] == "00:00":
                print("[DEBUG] Invalid deadline: Monday 00:00")
                return jsonify({'success': False, 'message': 'Cannot set deadline to Monday 00:00 — schedule starts then'}), 400   

        required_fields = ['title', 'description', 'priority', 'duration']
        if not data or not all(key in data for key in required_fields):
            print("[DEBUG] Missing required fields")
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        if data.get("mode") == "manual":
            new_task_id = handle_manual_task(data)
            day = data['day']
            time = data['time']
        elif data.get("mode") == "auto":
            new_task_id, day, time = handle_auto_task(data)
        else:
            print("[DEBUG] Invalid mode")
            return jsonify({'success': False, 'message': 'Invalid mode'}), 400

        if not new_task_id:
            print("[DEBUG] Failed to create task")
            return jsonify({'success': False, 'message': 'Failed to create task'}), 400

        return jsonify({'success': True, 'message': 'Task created successfully', 'task_id': new_task_id, 'day': day, 'time': time})

    except Exception as e:
        print("[DEBUG] Exception in add_task:", str(e))
        return jsonify({'success': False, 'message': 'Exception occurred', 'error': str(e)}), 400
    

def handle_manual_task(data):
    """Handles manually scheduled task creation."""
    if not all(key in data for key in ['day', 'time']):
        return None  # נחזיר None במקרה שאין נתונים

    start_hour = int(data['time'].split(":")[0])
    task_duration = int(data['duration'])
    end_hour = start_hour + task_duration

    if end_hour >= 24:
        # Add part to current day
        first_task_id = db.add_task(
            data['title'],
            data['description'],
            data['priority'],
            data['day'],
            data['time'],
            24 - start_hour,
            current_user.id
        )

        mark_task_as_busy(current_user.id, data['day'], data['time'], 24 - start_hour)

        # Add remaining to next day
        next_day = get_next_day(data['day'])
        db.add_task(
            data['title'],
            data['description'],
            data['priority'],
            next_day,
            "00:00",
            task_duration - (24 - start_hour),
            current_user.id
        )

        mark_task_as_busy(current_user.id, next_day, "00:00", task_duration - (24 - start_hour))

        return first_task_id  # נחזיר את ה-ID של החלק הראשון

    # Within same day
    new_task_id = db.add_task(
        data['title'],
        data['description'],
        data['priority'],
        data['day'],
        data['time'],
        data['duration'],
        current_user.id
    )

    mark_task_as_busy(current_user.id, data['day'], data['time'], int(data['duration']))

    return new_task_id


def handle_auto_task(data):
    print(f"[DEBUG] Trying to find slot for user {current_user.id} duration={data['duration']} until {data['deadline_day']} {data['deadline_time']}")
    """Handles auto-scheduled task creation using the availability manager."""
    if not all(key in data for key in ['deadline_day', 'deadline_time', 'priority']):
        return None

    try:
        day, time = find_time_slot(
            int(data['duration']),
            data['deadline_day'],
            data['deadline_time'],
            current_user.id,
            db,
            data['priority']
        )

        if not day or not time:
            return None

        # Save to database
        task_id = db.add_task(
            data['title'], 
            data['description'], 
            data['priority'], 
            day, 
            time, 
            data['duration'], 
            current_user.id
        )
        print(f"[DEBUG] Inserted task: {task_id}")

        # Update in-memory availability
        mark_task_as_busy(current_user.id, day, time, int(data['duration']))

        return task_id, day, time

    except Exception as e:
        print("Error in auto scheduling:", str(e))
        return None


    

@app.route('/delete_task/<int:task_id>', methods=['POST','DELETE'])
@login_required
def delete_task(task_id):
    """Deletes a task by ID, ensuring it belongs to the current user."""
    try:
        task = db.get_task_by_id(task_id, current_user.id)
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'}), 404

        db.delete_task(task_id, current_user.id)

        # Update in-memory availability
        from utils.availability_manager import mark_task_as_free
        mark_task_as_free(current_user.id, task['day'], task['time'], int(task['duration']))

        return jsonify({'success': True, 'message': 'Task deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
    

@app.route("/sync_task_to_google/<int:task_id>")
@login_required
def sync_task_to_google(task_id):
    """
    Syncs a single task to Google Calendar using the task ID.
    """
    try:
        # Retrieve the task from the database for the logged-in user
        task = db.get_task_by_id(task_id, current_user.id)
        if not task:
            flash("Task not found", "error")
            return redirect(url_for("tasks_page"))

        # Convert the task's day and time into a datetime object
        start_dt = convert_task_to_datetime(task["day"], task["time"])
        
        # Calculate the end time based on the task's duration
        end_dt = start_dt + timedelta(hours=task["duration"])

        # Create a new event in Google Calendar using the task's details
        create_event(
            summary=task["title"],
            description=task["description"],
            start_datetime=start_dt.isoformat(),
            end_datetime=end_dt.isoformat(),
            user_id=current_user.id
        )

        # Show success message to user
        flash("Task synced with Google Calendar!", "success")

    except Exception as e:
        # If an error occurs, show an error message to the user
        flash(f"Failed to sync task: {e}", "error")

    # Redirect back to the task list page
    return redirect(url_for("tasks_page"))

@app.route("/google-auth")
@login_required
def google_auth():
    """Starts the OAuth2 flow for Google Calendar connection."""
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    session['state'] = state
    session['user_id_for_google_auth'] = current_user.id
    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():
    """Handles Google's callback after user authorization."""
    session_state = session.get('state')
    request_state = request.args.get('state')

    if not session_state or not request_state:
        flash("Session expired. Please try again.", "error")
        return redirect(url_for("index"))

    if session_state != request_state:
        flash("Session mismatch. Please try connecting again.", "error")
        return redirect(url_for("index"))

    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            state=session_state,
            redirect_uri='http://localhost:5000/oauth2callback'
        )

        user_id = session.get('user_id_for_google_auth')
        if not user_id:
            flash("User ID missing. Please login again.", "error")
            return redirect(url_for("index"))

        save_credentials(flow, authorization_response_url=request.url, user_id=user_id)

        flash("Google Calendar connected successfully!", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"OAuth2 connection error: {str(e)}", "error")
        return redirect(url_for("index"))






@app.route("/google-disconnect")
@login_required
def google_disconnect():
    """Removes the saved Google Calendar credentials for the current user."""
    token_file = f'tokens/token_{current_user.id}.pickle'
    try:
        if os.path.exists(token_file):
            os.remove(token_file)
            flash("Disconnected from Google Calendar successfully.", "info")
        else:
            flash("You were not connected to Google Calendar.", "warning")
    except Exception as e:
        flash(f"Error disconnecting: {str(e)}", "error")
    
    return redirect(url_for("index"))



@app.context_processor
def inject_google_status():
    if current_user.is_authenticated:
        token_file = f'tokens/token_{current_user.id}.pickle'
        return {'google_connected': os.path.exists(token_file)}
    return {'google_connected': False}


@app.route('/import_google_events')
@login_required
def import_google_events():
    """
    Imports upcoming events from Google Calendar as tasks.
    Uses the next 20 upcoming events.
    """
    try:
        events = get_upcoming_events(user_id=current_user.id, max_results=20)
        imported = 0

        for event in events:
            title = event.get('summary', 'No Title')
            description = event.get('description', '')
            start = event['start'].get('dateTime')
            end = event['end'].get('dateTime')

            if not start or not end:
                continue

            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

            day = start_dt.strftime('%A')
            time = start_dt.strftime('%H:00')
            duration_hours = (end_dt - start_dt).total_seconds() / 3600
            duration = max(1, int(round(duration_hours)))

            db.add_task(title, description, "Medium", day, time, duration, current_user.id)
            imported += 1

        return jsonify({'success': True, 'message': f'{imported} events imported'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/import_google_tasks", methods=["POST"])
@login_required
def import_google_tasks():
    """
    Imports all events from the current week into the system,
    avoiding duplicates by checking existing task titles and time.
    """
    try:
        service = get_calendar_service(current_user.id)
        today = datetime.now(timezone.utc)
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_week.isoformat(),
            timeMax=end_of_week.isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        imported = 0

        for event in events:
            title = event.get('summary', 'No Title')
            description = event.get('description', '')
            start = event['start'].get('dateTime', '')
            end = event['end'].get('dateTime', '')

            if 'T' not in start or not end:
                continue

            dt_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            dt_end = datetime.fromisoformat(end.replace("Z", "+00:00"))

            day = dt_start.strftime('%A')
            hour = dt_start.strftime('%H:00')
            duration_hours = (dt_end - dt_start).total_seconds() / 3600
            duration = max(1, int(round(duration_hours)))

            # Avoid duplicate tasks
            existing_tasks = db.get_tasks_by_day_and_time(current_user.id, day, hour)
            if any(task['title'] == title for task in existing_tasks):
                continue

            db.add_task(title, description, "Medium", day, hour, duration, current_user.id)
            imported += 1

        flash(f"{imported} events imported from Google Calendar", "success")
        return redirect(url_for("weekly_schedule"))
    except Exception as e:
        flash(f"Error importing from Google Calendar: {str(e)}", "error")
        return redirect(url_for("weekly_schedule"))


@app.route("/sync_all_tasks_to_google", methods=["POST"])
@login_required
def sync_all_tasks_to_google():
    """
    Syncs all of the user's local tasks with Google Calendar.
    """
    try:
        tasks = db.get_tasks_json(current_user.id)
        synced = 0

        for task in tasks:
            start_dt = convert_task_to_datetime(task["day"], task["time"])
            end_dt = start_dt + timedelta(hours=task["duration"])

            create_event(
                summary=task["title"],
                description=task["description"],
                start_datetime=start_dt.isoformat(),
                end_datetime=end_dt.isoformat(),
                user_id=current_user.id
            )
            synced += 1

        flash(f"{synced} tasks synced with Google Calendar.", "success")
    except Exception as e:
        flash(f"Failed to sync tasks: {e}", "error")

    return redirect(url_for("weekly_schedule"))

def initialize_all_users_availability():
    """Load all users' tasks into memory when the server starts.""" 

    db = TaskDB()

    # Connect to the users database to fetch all user IDs
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    for user_id in user_ids:
        initialize_availability(user_id)  # Create empty weekly schedule
        tasks = db.get_tasks_json(user_id)  # Get all tasks of the user

        for task in tasks:
            mark_task_as_busy(
                user_id=user_id,
                day=task['day'],
                start_time=task['time'],
                duration=int(task['duration'])
            )

    print("[INFO] Finished loading all users' availability.")

# ==========================================
# Run the Flask Server
# ==========================================

if __name__ == "__main__":
    initialize_all_users_availability()
    app.run(debug=True)
