// Order of days used for scheduling grid
const DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// Run after DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
    const path = window.location.pathname;

    // Load tasks on specific pages
    if (path === "/tasks" || path === "/weekly-schedule") {
        fetchTasks();
    }

    // Google Calendar event import (manual trigger)
    document.getElementById('import-google-events')?.addEventListener('click', function () {
        fetch("/import_google_events")
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    fetchTasks();  // Refresh task view
                } else {
                    alert("Error importing: " + (data.error || "Unknown error"));
                }
            })
            .catch(error => {
                console.error("Failed to import events:", error);
                alert("Failed to import events");
            });
    });

    // Modal form submission (Add Task)
    const form = document.getElementById("add-task-form");
    if (form) {
        form.addEventListener("submit", addTask);
    }

    // Open modal when task button is clicked
    document.querySelectorAll(".add-task-button").forEach(button => {
        button.addEventListener("click", () => openModal("add-task-modal"));
    });

    // Close modal when clicking outside of modal content
    window.onclick = function (event) {
        if (event.target === document.getElementById("add-task-modal")) {
            closeModal("add-task-modal");
        }
    };
});

// Global notification system
function showNotification(message, type = "success") {
    const notification = document.getElementById('notification');
    if (!notification) return;

    notification.textContent = message;

    if (type === "success") {
        notification.style.backgroundColor = "#4caf50";
    } else if (type === "error") {
        notification.style.backgroundColor = "#f44336";
    } else if (type === "info") {
        notification.style.backgroundColor = "#2196f3";
    }

    notification.style.display = "block";

    setTimeout(() => {
        notification.style.display = "none";
    }, 3000);
}

// Add new task via modal form (manual or automatic mode)
function addTask(event) {
    event.preventDefault();
    const startTime = performance.now();

    const task = document.getElementById('task').value;
    const description = document.getElementById('description').value;
    const priority = document.getElementById('priority').value;
    const duration = parseInt(document.getElementById('duration').value);
    const isManual = document.getElementById('manual-time-toggle').checked;

    const payload = {
        title: task,
        description,
        priority,
        duration,
        mode: isManual ? 'manual' : 'auto'
    };

    if (isManual) {
        payload.day = document.getElementById('day').value;
        payload.time = document.getElementById('time').value;
    } else {
        payload.deadline_day = document.getElementById('deadline-day').value;
        payload.deadline_time = document.getElementById('deadline-time').value;
    }

    fetch("/add_task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        const endTime = performance.now();
        console.log(`Task added in ${(endTime - startTime).toFixed(2)} ms`);

        if (data.success) {
            closeModal('add-task-modal');

            insertTaskIntoTable(data.task_id, task, description, priority, data.day, data.time);

            insertTaskIntoWeeklySchedule({
                task_id: data.task_id,
                title: task,
                day: data.day,
                time: data.time,
                duration
            });

            showNotification(`Task added successfully for ${data.day} at ${data.time}`, "success");
        } else {
            showNotification("Failed to add task: " + data.message, "error");
        }
    })
    .catch(error => {
        console.error("Error adding task:", error);
        showNotification("An error occurred while adding the task.", "error");
    });
}

// Populate tasks to both table view and weekly grid
function populateTasks(tasks) {
    const high = document.getElementById('high-priority-tasks');
    const medium = document.getElementById('medium-priority-tasks');
    const low = document.getElementById('low-priority-tasks');
    const grid = document.getElementById('myTable');

    if (high && medium && low) {
        high.innerHTML = '';
        medium.innerHTML = '';
        low.innerHTML = '';

        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.id = `task-${task.id}`;
            row.innerHTML = `
                <td>${task.title}</td>
                <td>${task.description}</td>
                <td>${task.day} ${task.time} - ${(parseInt(task.time.split(':')[0]) + task.duration).toString().padStart(2, '0')}:00</td>
                <td><button onclick="deleteTask(${task.id})">Delete</button></td>
            `;

            switch (task.priority) {
                case 'High': high.appendChild(row); break;
                case 'Medium': medium.appendChild(row); break;
                case 'Low': low.appendChild(row); break;
                default: console.warn("Unknown priority:", task.priority);
            }
        });
    }

    if (grid) {
        tasks.forEach(task => insertTaskIntoWeeklySchedule(task));
    }
}

// Place task visually into weekly schedule grid
function insertTaskIntoWeeklySchedule(task) {
    const startHour = parseInt(task.time.split(':')[0]);
    const duration = parseInt(task.duration) || 1;

    for (let h = startHour; h < startHour + duration; h++) {
        const hourStr = `${(h % 24).toString().padStart(2, '0')}:00`;
        const dayIndex = (DAYS_ORDER.indexOf(task.day) + Math.floor(h / 24)) % 7;
        const currentDay = DAYS_ORDER[dayIndex];
        const cell = document.querySelector(`td[data-day='${currentDay}'][data-hour='${hourStr}']`);

        if (cell) {
            cell.classList.add('has-task', 'clickable');
            cell.title = task.title;
            cell.setAttribute('data-task-id', task.task_id || task.id);
            cell.onclick = () => openTasksModal(currentDay, hourStr);
        }
    }
}

// Insert task into the table under its priority group
function insertTaskIntoTable(taskId, title, description, priority, day, time) {
    if (window.location.pathname !== "/tasks") return;

    const tbody = document.getElementById(`${priority.toLowerCase()}-priority-tasks`);
    if (!tbody) return;

    const row = document.createElement('tr');
    row.id = `task-${taskId}`;
    row.innerHTML = `
        <td>${title}</td>
        <td>${description}</td>
        <td>${day} ${time}</td>
        <td><button onclick="deleteTask(${taskId})">Delete</button></td>
    `;
    tbody.appendChild(row);
}

// Fetch tasks from the API and populate in UI
async function fetchTasks() {
    try {
        const response = await fetch("/api/tasks");
        const contentType = response.headers.get("Content-Type") || "";
        const currentPath = window.location.pathname;
        const protectedPages = ["/tasks", "/weekly-schedule"];

        if (!response.ok || !contentType.includes("application/json")) {
            if (protectedPages.includes(currentPath)) {
                showNotification("Please log in to access this page.");
            }
            return;
        }

        const data = await response.json();
        if (!data) return;

        if (data.success && Array.isArray(data.tasks)) {
            populateTasks(data.tasks);
        } else {
            showNotification("No tasks available.");
        }
    } catch (error) {
        console.error("Error fetching tasks:", error);
    }
}

// Modal logic
function openModal(modalId) {
    document.getElementById(modalId).style.display = "block";
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = "none";
}


// Delete task by ID and remove from table without refresh
async function deleteTask(taskId) {
    fetch(`/delete_task/${taskId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // מחק את השורה מהטבלה בלי רענון
                const row = document.getElementById(`task-${taskId}`);
                if (row) {
                    row.remove();
                }
                removeTaskFromWeeklySchedule(taskId);
                showNotification('Task deleted successfully!', 'success');
            } else {
                showNotification('Failed to delete task: ' + data.message, 'error');
            }
        })
        .catch(error => console.error('Error deleting task:', error));
}

// Open modal with all tasks for a specific time slot
function openTasksModal(taskDay, taskHour) {
    const modal = document.getElementById('taskModal');
    if (modal) {
        const modalContent = modal.querySelector('.modal-content');
        modalContent.innerHTML = '';

        const closeBtn = document.createElement('span');
        closeBtn.classList.add('close-modal-btn');
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = () => closeModal('taskModal');

        const title = document.createElement('strong');
        title.innerText = `Tasks for ${taskDay} at ${taskHour}:`;

        modalContent.appendChild(closeBtn);
        modalContent.appendChild(title);
        modalContent.appendChild(document.createElement('br'));

        clearExistingTasks(modalContent);

        fetch(`/api/tasks?day=${encodeURIComponent(taskDay)}&time=${encodeURIComponent(taskHour)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.tasks.length > 0) {
                    data.tasks.forEach(task => {
                        if (!modalContent.querySelector(`[data-task-id='${task.id}']`)) {
                            const taskDiv = document.createElement('div');
                            taskDiv.classList.add('task');
                            taskDiv.dataset.taskId = task.id;
                            taskDiv.textContent = `${task.title}: ${task.description}`;
                            modalContent.appendChild(taskDiv);
                        }
                    });
                } else {
                    const noTask = document.createElement('p');
                    noTask.textContent = 'No tasks found for this time.';
                    modalContent.appendChild(noTask);
                }

                openModal('taskModal');
            })
            .catch(error => {
                console.error('Error fetching tasks:', error);
                const errorMsg = document.createElement('p');
                errorMsg.textContent = 'Error loading tasks.';
                modalContent.appendChild(errorMsg);
            });
    }
}

// Clear existing task nodes in modal to avoid duplication
function clearExistingTasks(container) {
    const tasks = container.querySelectorAll('.task');
    tasks.forEach(task => task.remove());
}