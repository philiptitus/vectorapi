

from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.utils.html import strip_tags
from django.conf import settings
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import random
import string

CREDENTIALS_FILE = os.path.join('config', 'credentials', 'google_calendar_credentials.json')


SCOPES = ['https://www.googleapis.com/auth/calendar']





from datetime import timedelta
import logging

# Set up logging
logging.basicConfig(
    filename='calendar_event_debug.log',  # Log file name
    level=logging.DEBUG,  # Log everything for debugging
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_calendar_event(service, summary, description, location, start_time, end_time):
    """
    Creates a Google Calendar event using the provided service.
    """
    # Debug: Initializing event creation
    print("Initializing Google Calendar event creation...")
    logging.debug("Starting Google Calendar event creation.")

    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC',  # Replace 'UTC' with the correct timezone if needed
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC',  # Replace 'UTC' with the correct timezone if needed
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # Email reminder 1 day before
                {'method': 'popup', 'minutes': 10},  # Popup reminder 10 minutes before
            ],
        },
    }

    # Debug: Print and log the event data being sent
    print(f"Event data being sent to Google Calendar API: {event}")
    logging.debug(f"Event payload: {event}")

    try:
        # Create the event
        created_event = service.events().insert(calendarId='primary', body=event).execute()

        # Debug: Print and log the created event response
        print(f"Event successfully created: {created_event.get('htmlLink')}")
        logging.info(f"Event successfully created. Link: {created_event.get('htmlLink')}")

        return created_event

    except Exception as e:
        # Debug: Print and log the exception details
        print(f"Error while creating event: {str(e)}")
        logging.error(f"Error creating Google Calendar event: {str(e)}", exc_info=True)
        raise  # Re-raise the exception for further handling



def generate_state():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

from google_auth_oauthlib.flow import Flow


# Constants
REDIRECT_URI = 'http://localhost:3000/oauth/callback'  # Must match Google Cloud Console settings


# def get_google_calendar_service(user):
#     """
#     Gets the Google Calendar API service for the given user.
#     """
#     state = generate_state()

#     # Token storage path - customize based on your setup
#     token_path = os.path.join('config', 'tokens', f'token_{user.id}.json')

#     creds = None
#     if os.path.exists(token_path):
#         creds = Credentials.from_authorized_user_file(token_path, SCOPES)

#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             # Use Flow instead of InstalledAppFlow for web-based redirect handling
#             flow = Flow.from_client_secrets_file(
#                 CREDENTIALS_FILE,
#                 scopes=SCOPES,
#                 redirect_uri=REDIRECT_URI,  # Explicitly set the redirect URI
#             )
#             # Generate authorization URL for the user to complete the OAuth flow
#             auth_url, _ = flow.authorization_url(
#                 access_type='offline',
#                 include_granted_scopes='true',
#                 state=state
#             )
#             print(f"Please authorize this app by visiting this URL: {auth_url}")
#             return auth_url  # Redirect user to this URL (frontend should handle this)

#         # After receiving the authorization response, fetch credentials
#         flow.fetch_token(state=state)
#         creds = flow.credentials

#         # Save the credentials for the next run
#         os.makedirs(os.path.dirname(token_path), exist_ok=True)
#         with open(token_path, 'w') as token:
#             token.write(creds.to_json())

#     # Return the Google Calendar service if credentials are valid
#     return build('calendar', 'v3', credentials=creds)
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def get_google_calendar_service(user):
    """
    Gets the Google Calendar API service for the given user.
    """
    state = generate_state()
    print(f"Generated state: {state}")

    # Token storage path - customize based on your setup
    token_path = os.path.join('config', 'tokens', f'token_{user.id}.json')
    print(f"Token path: {token_path}")

    creds = None
    if os.path.exists(token_path):
        print(f"Token file exists at {token_path}")
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        print(f"Credentials loaded from file: {creds}")
    if not creds or not creds.valid:
        print("Credentials are not valid or do not exist")
        if creds and creds.expired and creds.refresh_token:
            print("Credentials are expired but refresh token is available")
            creds.refresh(Request())
            print("Credentials refreshed")
        else:
            print("No valid credentials, initiating OAuth flow")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            flow.redirect_uri = 'http://localhost:8000/'
            print(f"Redirect URI set to: {flow.redirect_uri}")

            auth_url, _ = flow.authorization_url(access_type='offline', state=state)
            print(f"Please authorize this app by visiting this URL: {auth_url}")

            return auth_url

            # creds = flow.run_local_server(port=8000, state=state)

        # Save the credentials for the next run
    #     os.makedirs(os.path.dirname(token_path), exist_ok=True)
    #     with open(token_path, 'w') as token:
    #         token.write(creds.to_json())
    #     print(f"Credentials saved to {token_path}")

    # return build('calendar', 'v3', credentials=creds)




# def get_google_calendar_service(user):
#     """
#     Gets the Google Calendar API service for the given user.
#     """
#     state = generate_state()

#     # Token storage path - customize based on your setup
#     token_path = os.path.join('config', 'tokens', f'token_{user.id}.json')

#     creds = None
#     if os.path.exists(token_path):
#         creds = Credentials.from_authorized_user_file(token_path, SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
#             auth_url, _ = flow.authorization_url(access_type='offline', state=state)
#             print(f"AUTH URL:  {auth_url}")
#             return auth_url

#         # Save the credentials for the next run
#         os.makedirs(os.path.dirname(token_path), exist_ok=True)
#         with open(token_path, 'w') as token:
#             token.write(creds.to_json())

#     return build('calendar', 'v3', credentials=creds)


def send_normal_email(data):
    # Load and render the template with context
    template = Template(data['email_body'])
    context = Context(data.get('context', {}))
    html_content = template.render(context)
    text_content = strip_tags(html_content)  # Fallback text content

    # Create email message
    email = EmailMultiAlternatives(
        subject=data['email_subject'],
        body=html_content,  # Plain text content for email clients that don't support HTML
        from_email=settings.EMAIL_HOST_USER,
        to=[data['to_email']],
    )
    email.attach_alternative(html_content, "text/html")  # Attach the HTML version

    # Send email
    email.send()


