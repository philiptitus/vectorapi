import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse

# SCOPES define the level of access we want (access to Google Calendar).
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_google_calendar_service(user):
    credentials = get_user_google_credentials(user)
    if not credentials:
        return redirect(reverse('google_auth_start'))

    # Build the service with credentials
    service = build('calendar', 'v3', credentials=credentials)
    return service

def get_user_google_credentials(user):
    token = user.google_token
    refresh_token = user.google_refresh_token
    if not token:
        return None
    
    credentials = Credentials(
        token=token,
        refresh_token=refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_uri='https://oauth2.googleapis.com/token',
        scopes=SCOPES,
    )
    
    return credentials


def google_auth_start(request):
    flow = InstalledAppFlow.from_client_secrets_file(
        settings.GOOGLE_CREDENTIALS_PATH, SCOPES
    )
    authorization_url, state = flow.authorization_url(access_type='offline')
    request.session['state'] = state
    return redirect(authorization_url)



def google_auth_callback(request):
    state = request.session['state']
    flow = InstalledAppFlow.from_client_secrets_file(
        settings.GOOGLE_CREDENTIALS_PATH, SCOPES, state=state
    )
    
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials
    # Save the credentials to the user’s CustomUser fields
    request.user.google_token = credentials.token
    request.user.google_refresh_token = credentials.refresh_token
    request.user.save()

    return HttpResponse('Authentication successful!')
