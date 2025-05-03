import os
import pickle
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Google Calendar API settings
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'client_secret_1023653706146-dpktj6ab93uripnivbslhpi2ugo8t6o3.apps.googleusercontent.com.json'

def get_calendar_flow():
    """Creates an OAuth2 flow object for Google Calendar authentication."""
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:5000/oauth2callback'
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {'auth_url': auth_url, 'flow': flow}

def save_credentials(flow, authorization_response_url, user_id):
    """Saves OAuth2 credentials to a user-specific token file."""
    flow.fetch_token(authorization_response=authorization_response_url)
    creds = flow.credentials
    token_file = f'tokens/token_{user_id}.pickle'
    os.makedirs(os.path.dirname(token_file), exist_ok=True)
    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)

def get_calendar_service(user_id):
    """Loads credentials from a user-specific token file and returns a Calendar service."""
    token_file = f'tokens/token_{user_id}.pickle'
    creds = None

    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("User not authenticated with Google Calendar. Please connect first.")

    return build('calendar', 'v3', credentials=creds)

def create_event(summary, description, start_datetime, end_datetime, user_id):
    """Creates an event in the user's Google Calendar."""
    service = get_calendar_service(user_id)

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_datetime,
            'timeZone': 'Asia/Jerusalem',
        },
        'end': {
            'dateTime': end_datetime,
            'timeZone': 'Asia/Jerusalem',
        }
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event

def get_upcoming_events(user_id, max_results=10):
    """Fetches upcoming events from the user's Google Calendar."""
    service = get_calendar_service(user_id)

    events_result = service.events().list(
        calendarId='primary',
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])
