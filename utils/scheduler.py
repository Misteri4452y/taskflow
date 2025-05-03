from datetime import datetime
from utils.availability_manager import initialize_availability_for_user

# Preferred scheduling hours per task priority
PRIORITY_HOURS = {
    "High": list(range(8, 13)),    # 08:00–12:00
    "Medium": list(range(12, 17)), # 12:00–16:00
    "Low": list(range(16, 23))     # 16:00–22:00
}

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def previous_day(current_day):
    """Returns the previous day given a day name."""
    idx = DAYS_ORDER.index(current_day)
    return DAYS_ORDER[(idx - 1) % 7]

def is_past_deadline(current_day, deadline_day):
    """Determines if the current day is after the given deadline day."""
    current_index = DAYS_ORDER.index(current_day)
    deadline_index = DAYS_ORDER.index(deadline_day)
    return current_index > deadline_index

def find_time_slot(duration, deadline_day, deadline_time, user_id, db, priority="Medium"):
    """
    Finds the earliest available time slot before the deadline based on priority.

    Args:
        duration (int): Task duration in hours.
        deadline_day (str): Day by which the task must be scheduled.
        deadline_time (str): Time on the deadline day (HH:MM).
        user_id (str/int): The user's ID.
        db: Database interface to retrieve tasks.
        priority (str): Task priority ("High", "Medium", "Low").

    Returns:
        Tuple (day, time) if found, else (None, None).
    """
    if deadline_time == "00:00":
        deadline_time = "23:59"
        deadline_day = previous_day(deadline_day)

    # Initialize availability map: True = available
    availability = {day: {f"{hour:02d}:00": True for hour in range(24)} for day in DAYS_ORDER}
    tasks = db.get_tasks_json(user_id)

    # Mark existing task slots as busy
    for task in tasks:
        task_day = task['day']
        start_hour = int(task['time'].split(":")[0])
        task_duration = int(task['duration'])
        for h in range(start_hour, start_hour + task_duration):
            h_mod = h % 24
            hour_str = f"{h_mod:02d}:00"
            if task_day in availability and hour_str in availability[task_day]:
                availability[task_day][hour_str] = False

    # Determine days to scan based on deadline
    start_index = 0  # Sunday
    end_index = DAYS_ORDER.index(deadline_day)
    if end_index < start_index:
        end_index += 7

    days_to_check = [DAYS_ORDER[offset % 7] for offset in range(start_index, end_index + 1)]
    preferred_hours = PRIORITY_HOURS.get(priority, list(range(8, 22)))

    # First pass: try preferred hours
    for day in days_to_check:
        for hour in preferred_hours:
            if _is_slot_available(availability, day, hour, duration, deadline_day, deadline_time):
                print(f"[DEBUG] Found preferred slot: {day} {hour}:00 for {duration}h")
                return day, f"{hour:02d}:00"

    # Second pass: try all hours if preferred failed
    for day in days_to_check:
        for hour in range(24):
            if _is_slot_available(availability, day, hour, duration, deadline_day, deadline_time):
                print(f"[DEBUG] Found fallback slot: {day} {hour}:00 for {duration}h")
                return day, f"{hour:02d}:00"

    # No available slots found
    print("[DEBUG] No available slot found")
    return None, None

def _is_slot_available(availability, day, start_hour, duration, deadline_day, deadline_time):
    """
    Verifies whether a slot is free and does not exceed the deadline.

    Args:
        availability (dict): Availability map.
        day (str): Day to check.
        start_hour (int): Starting hour.
        duration (int): Duration of the task.
        deadline_day (str): Deadline day.
        deadline_time (str): Deadline hour in HH:MM format.

    Returns:
        bool: True if slot is valid and available.
    """
    if day == deadline_day:
        deadline_hour = int(deadline_time.split(":")[0])
        if start_hour >= deadline_hour or start_hour + duration > deadline_hour:
            return False

    for offset in range(duration):
        hour = (start_hour + offset) % 24
        hour_str = f"{hour:02d}:00"
        if not availability.get(day, {}).get(hour_str, False):
            return False

    return True

def create_availability_map(tasks):
    """
    Reconstructs an availability map based on a task list.

    Used for benchmarking or reconstructing in-memory availability state.

    Args:
        tasks (list): List of task dictionaries.

    Returns:
        dict: Availability map with True/False per hour per day.
    """
    availability = {day: {f"{hour:02d}:00": True for hour in range(24)} for day in DAYS_ORDER}

    for task in tasks:
        task_day = task['day']
        start_hour = int(task['time'].split(":")[0])
        task_duration = int(task['duration'])

        for h in range(start_hour, start_hour + task_duration):
            h_mod = h % 24
            hour_str = f"{h_mod:02d}:00"
            if task_day in availability and hour_str in availability[task_day]:
                availability[task_day][hour_str] = False

    return availability
