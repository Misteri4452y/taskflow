document.addEventListener("DOMContentLoaded", function () {
    const path = window.location.pathname;

    // Load tasks only on relevant pages
    if (path === "/tasks" || path === "/weekly-schedule") {
        fetchTasks();
    }

    // Import events from Google Calendar (manual trigger)
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

    // Submit handler for "Add Task" modal
    const form = document.getElementById("add-task-form");
    if (form) {
        form.addEventListener("submit", addTask);
    }

    // Close modal when clicking outside of modal content
    document.querySelectorAll(".add-task-button").forEach(button => {
        button.addEventListener("click", () => openModal("add-task-modal"));
    });

    window.onclick = function (event) {
        if (event.target === document.getElementById("add-task-modal")) {
            closeModal("add-task-modal");
        }
    };
});

// Notification utility
function showNotification(message) {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.textContent = message;
        notification.style.display = 'block';
        setTimeout(() => {
            notification.style.display = 'none';
        }, 4000);
    }
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

// Add task (manual or auto mode)
function addTask(event) {
    event.preventDefault();

    const task = document.getElementById('task').value;
    const description = document.getElementById('description').value;
    const priority = document.getElementById('priority').value;
    const duration = parseInt(document.getElementById('duration').value);
    const isManual = document.getElementById('manual-time-toggle').checked;

    const payload = {
        title: task,
        description: description,
        priority: priority,
        duration: duration,
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
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                closeModal('add-task-modal');
                fetchTasks();
            } else {
                alert("Failed to add task: " + data.message);
            }
        })
        .catch(error => {
            console.error("Error adding task:", error);
        });
}

// Render tasks to the task tables and weekly schedule
function populateTasks(tasks) {
    const highPriorityTasks = document.getElementById('high-priority-tasks');
    const mediumPriorityTasks = document.getElementById('medium-priority-tasks');
    const lowPriorityTasks = document.getElementById('low-priority-tasks');
    const weeklySchedule = document.getElementById('myTable');

    if (highPriorityTasks && mediumPriorityTasks && lowPriorityTasks) {
        highPriorityTasks.innerHTML = '';
        mediumPriorityTasks.innerHTML = '';
        lowPriorityTasks.innerHTML = '';

        tasks.forEach(task => {
            const taskRow = document.createElement('tr');
            taskRow.innerHTML = `
                <td>${task.title}</td>
                <td>${task.description}</td>
                <td>${task.day} ${task.time}-${(parseInt(task.time.split(':')[0]) + task.duration).toString().padStart(2, '0')}:00</td>
                <td><button onclick="deleteTask(${task.id})">Delete</button></td>
            `;

            switch (task.priority) {
                case 'High':
                    highPriorityTasks.appendChild(taskRow);
                    break;
                case 'Medium':
                    mediumPriorityTasks.appendChild(taskRow);
                    break;
                case 'Low':
                    lowPriorityTasks.appendChild(taskRow);
                    break;
                default:
                    console.error('Unknown priority:', task.priority);
            }
        });
    }

    // Weekly schedule rendering
    if (weeklySchedule) {
        tasks.forEach(task => {
            const taskDay = task.day;
            const startHour = parseInt(task.time.split(':')[0]);
            const duration = parseInt(task.duration) || 1;

            for (let h = startHour; h < startHour + duration; h++) {
                const hourStr = `${h.toString().padStart(2, '0')}:00`;
                const cell = document.querySelector(`td[data-day='${taskDay}'][data-hour='${hourStr}']`);
                if (cell) {
                    cell.classList.add('has-task', 'clickable');
                    cell.title = task.title;
                    cell.addEventListener('click', () => openTasksModal(taskDay, task.time));
                }
            }
        });
    }
}

// Delete task by ID and refresh
function deleteTask(taskId) {
    fetch(`/delete_task/${taskId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert('Failed to delete task: ' + data.message);
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
