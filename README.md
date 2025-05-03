# TaskFlow

A smart weekly task manager with Google Calendar sync built using Flask.

## Features

- 📝 Create tasks manually or automatically based on availability
- 🗓️ View your tasks in a weekly schedule table
- 🎯 Prioritize tasks (High, Medium, Low)
- 🔄 Sync tasks with Google Calendar
- 📥 Import events from Google Calendar
- 🔒 Secure login and registration system (passwords are hashed securely)
- ✨ Modern, dynamic frontend (HTML, CSS, JavaScript)

## Tech Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **Authentication:** Flask-Login + Secure password hashing
- **Calendar Integration:** Google Calendar API (OAuth2)

## Security

- Passwords are securely hashed using `werkzeug.security` functions (not stored in plain text).
- OAuth tokens are saved per user securely in the server.

## How It Works

- Tasks are stored in a local SQLite database.
- Manual tasks are placed on a specific day/hour.
- Auto tasks are scheduled in the first available slot based on priority and deadline.
- A RAM-based availability map keeps scheduling O(1).
- Tasks can be synced both ways with Google Calendar.

## Important Note about Google Calendar Integration

During development, Google OAuth2 authentication will work only for Google accounts added as **Test Users** in the Google Cloud Console.  
To allow anyone to log in with their Google account, you need to **Publish your app** in the Google API Console and pass Google's verification process.  
→ [Go to Google Cloud Console](https://console.cloud.google.com/apis/credentials)

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/taskflow.git
   cd taskflow
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate   # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your Google Cloud project, configure OAuth Consent Screen, and download your `client_secret.json`.

5. Run the app locally:

   On Linux/Mac:
   ```bash
   python app.py
   ```

   On Windows:
   ```bash
   py app.py
   ```

6. Open your browser and visit:
   ```
   http://localhost:5000
   ```

## Folder Structure

```
/taskflow
    /static
        /css
        /js
    /templates
    /db
    /utils
    /tokens
    app.py
    README.md
    requirements.txt
```

## License

This project is licensed under the MIT License.