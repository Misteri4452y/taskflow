import sqlite3

# Establish a connection to the database
conn = sqlite3.connect('gta.db')
cursor = conn.cursor()

# Fetch and print all tasks from the tasks table
cursor.execute("SELECT * FROM tasks;")
tasks = cursor.fetchall()
print("Tasks:")
for task in tasks:
    print(task)

# Fetch and print all users from the users table
cursor.execute("SELECT * FROM users;")
users = cursor.fetchall()
print("\nUsers:")
for user in users:
    print(user)

# Close the database connection
conn.close()
