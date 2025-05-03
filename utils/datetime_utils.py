from datetime import datetime, timedelta

def convert_task_to_datetime(day: str, time: str) -> datetime:
    """
    Converts a day of the week and time string (e.g., "Monday", "14:00") into
    a datetime object based on the upcoming occurrence of that day.

    Args:
        day (str): Day of the week (e.g., "Monday").
        time (str): Time in HH:MM format (e.g., "14:00").

    Returns:
        datetime: A datetime object representing the next occurrence of the given day and time.

    Raises:
        ValueError: If the provided day is not a valid weekday.
    """
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Validate input day
    if day not in days_order:
        raise ValueError("Invalid day: must be a day of the week")

    # Get today's date and weekday index (0 = Monday, 6 = Sunday)
    today = datetime.today()
    today_weekday = today.weekday()

    # Find index of the target weekday
    target_weekday = days_order.index(day)

    # Calculate how many days ahead the target day is
    days_ahead = (target_weekday - today_weekday) % 7

    # Extract hour from the time string
    hour = int(time.split(":")[0])

    # Set the hour and zero minutes/seconds, then add the days offset
    task_date = today.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)

    return task_date
