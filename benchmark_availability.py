import time
import sys
import os

# Ensure the project root is in the Python path (for relative imports)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.availability_manager import mark_task_as_busy, initialize_availability_for_user
from db.task_db import TaskDB
from utils.scheduler import create_availability_map

# Example benchmark: Test for a specific user (user_id = 1)
user_id = 1

# Make sure RAM-based availability is initialized for the user
initialize_availability_for_user(user_id)

# Optional: Number of repetitions to amplify timing (can be used for stress test)
repeats = 1

# ---------- RAM-based update benchmark ----------
start_ram = time.perf_counter()
for _ in range(repeats):
    # Simulate marking a task as busy in memory (RAM)
    mark_task_as_busy(user_id, "Wednesday", "14:00", 2)
end_ram = time.perf_counter()
print(f"[BENCHMARK] RAM-based update took: {end_ram - start_ram:.8f} seconds")

# ---------- DB-based full availability map rebuild ----------
db = TaskDB()
all_tasks = db.get_tasks_json(user_id)

start_db = time.perf_counter()
for _ in range(repeats):
    # Simulate rebuilding the entire availability map from database tasks
    availability_map = create_availability_map(all_tasks)
end_db = time.perf_counter()
print(f"[BENCHMARK] DB-based availability creation took: {end_db - start_db:.8f} seconds")
