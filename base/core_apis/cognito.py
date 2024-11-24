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
        # Return the tokens if the request is successful
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

    if response.status_code == 200:
        return response.json()  # User information in JSON format
    else:
        print(f"Error fetching user info: {response.status_code} - {response.text}")
        return None


if __name__ == '__main__':
    # You can replace this with any authorization code for testing
    auth_code = input("Enter the authorization code: ")

    # Step 1: Exchange authorization code for tokens
    token_response = exchange_code_for_tokens(auth_code)

    if token_response:
        print("Token Response:", token_response)
        
        # Step 2: Get user info using the access token
        access_token = token_response.get('access_token')
        if access_token:
            user_info = get_user_info(access_token)
            print("User Info:", user_info)
        else:
            print("Access token not found in the token response.")
    else:
        print("Failed to exchange the authorization code for tokens.")
