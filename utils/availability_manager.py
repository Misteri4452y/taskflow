from datetime import datetime

# Define the order of days for consistency
DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# In-memory availability map: { user_id: { day: { hour: bool } } }
user_availability = {}

def initialize_availability_for_user(user_id):
    """
    Initializes the availability map for a user if it doesn't already exist.
    All hours are initially set as free (True).
    """
    if user_id not in user_availability:
        user_availability[user_id] = {
            day: {f"{hour:02d}:00": True for hour in range(24)}
            for day in DAYS_ORDER
        }

def initialize_availability(user_id):
    """
    Reinitializes (overwrites) the availability map for a user.
    All time slots across the week are marked as free.
    """
    user_availability[user_id] = {
        day: {f"{hour:02d}:00": True for hour in range(24)}
        for day in DAYS_ORDER
    }

def mark_task_as_busy(user_id, day, start_time, duration):
    """
    Marks a consecutive block of hours as busy (False) for a given user.
    
    Parameters:
    - user_id (int): ID of the user
    - day (str): Day of the task (e.g., "Wednesday")
    - start_time (str): Start time in "HH:MM" format (e.g., "14:00")
    - duration (int): Number of hours to mark as busy
    """
    if user_id not in user_availability:
        initialize_availability_for_user(user_id)

    start_hour = int(start_time.split(":")[0])

    for offset in range(duration):
        hour = (start_hour + offset) % 24  # Wrap around after 23
        hour_str = f"{hour:02d}:00"
        user_availability[user_id][day][hour_str] = False

def mark_task_as_free(user_id, day, start_time, duration):
    """
    Marks a consecutive block of hours as free (True), typically when a task is deleted.
    """
    if user_id not in user_availability:
        return  # No availability to update

    start_hour = int(start_time.split(":")[0])

    for offset in range(duration):
        hour = (start_hour + offset) % 24
        hour_str = f"{hour:02d}:00"
        user_availability[user_id][day][hour_str] = True

def is_slot_free(user_id, day, start_time, duration):
    """
    Checks if all hours in a block are free starting at a specific time.

    Returns:
    - True if all requested time slots are free
    - False if any slot is occupied
    """
    if user_id not in user_availability:
        initialize_availability(user_id)

    start_hour = int(start_time.split(":")[0])

    for offset in range(duration):
        hour = (start_hour + offset) % 24
        hour_str = f"{hour:02d}:00"
        if not user_availability[user_id][day].get(hour_str, False):
            return False
    return True
