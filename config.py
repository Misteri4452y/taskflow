# config.py

# Flask settings
SECRET_KEY = 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
SESSION_TYPE = 'filesystem'
SESSION_PERMANENT = True

# Google Calendar API
CREDENTIALS_FILE = 'client_secret_1023653706146-dpktj6ab93uripnivbslhpi2ugo8t6o3.apps.googleusercontent.com.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = 'http://localhost:5000/oauth2callback'
