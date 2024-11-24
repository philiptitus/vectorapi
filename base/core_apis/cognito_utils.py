# cognito_utils.py

import requests
from django.conf import settings

CLIENT_ID = settings.CLIENT_ID
REDIRECT_URI = settings.REDIRECT_URI
COGNITO_DOMAIN = settings.COGNITO_DOMAIN
TOKEN_ENDPOINT = f'{COGNITO_DOMAIN}/oauth2/token'
USERINFO_ENDPOINT = f'{COGNITO_DOMAIN}/oauth2/userInfo'


def exchange_code_for_tokens(auth_code):
    """
    Exchanges the authorization code for access and ID tokens
    """
    data = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(TOKEN_ENDPOINT, data=data, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching tokens: {response.status_code} - {response.text}")
        return None


def get_user_info(access_token):
    """
    Fetch user information using the access token
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(USERINFO_ENDPOINT, headers=headers)
    print(response)

    if response.status_code == 200:
        return response.json()  # User information in JSON format
    else:
        print(f"Error fetching user info: {response.status_code} - {response.text}")
        return None
