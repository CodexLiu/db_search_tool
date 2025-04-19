import os
import requests
import webbrowser
from dotenv import load_dotenv, set_key
import time

def load_env():
    """Load environment variables from .env file"""
    # Look for .env in the project root, not in utils directory
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)
    return {
        'app_key': os.getenv('app_key'),
        'app_secret': os.getenv('app_secret'),
        'current_access_token': os.getenv('current_access_token'),
        'refresh_token': os.getenv('refresh_token')
    }

def save_to_env(key, value):
    """Save a key-value pair to the .env file"""
    # Look for .env in the project root, not in utils directory
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    set_key(env_path, key, value)

def get_refresh_token():
    """
    Get a refresh token using the OAuth flow.
    This is a one-time operation that requires user interaction.
    """
    env_vars = load_env()
    app_key = env_vars['app_key']
    app_secret = env_vars['app_secret']
    
    # Step 1: Create the OAuth URL with offline access
    auth_url = f"https://www.dropbox.com/oauth2/authorize?client_id={app_key}&response_type=code&token_access_type=offline"
    
    # Step 2: Open the URL in a browser for the user to authorize
    print(f"Opening browser to authorize the app. Please login and authorize access.")
    webbrowser.open(auth_url)
    
    # Step 3: Get the authorization code from the user
    auth_code = input("Enter the authorization code from the browser: ")
    
    # Step 4: Exchange the authorization code for tokens
    token_url = "https://api.dropbox.com/oauth2/token"
    auth = (app_key, app_secret)
    data = {
        'code': auth_code,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(token_url, auth=auth, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        
        if not refresh_token:
            print("Error: No refresh token in response. Make sure token_access_type=offline was included in the auth URL.")
            return None, None
            
        # Save tokens to .env
        save_to_env('current_access_token', access_token)
        save_to_env('refresh_token', refresh_token)
        
        print("Successfully obtained and saved refresh and access tokens.")
        return refresh_token, access_token
    else:
        print(f"Error getting tokens: {response.status_code}")
        print(response.text)
        return None, None

def get_access_token():
    """
    Get a new access token using the refresh token.
    If no refresh token exists, call get_refresh_token first.
    """
    env_vars = load_env()
    refresh_token = env_vars['refresh_token']
    app_key = env_vars['app_key']
    app_secret = env_vars['app_secret']
    
    # If no refresh token, get one
    if not refresh_token:
        print("No refresh token found. Starting authorization process...")
        refresh_token, access_token = get_refresh_token()
        if access_token:
            return access_token
        return None
    
    # Use refresh token to get a new access token
    token_url = "https://api.dropbox.com/oauth2/token"
    data = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'client_id': app_key,
        'client_secret': app_secret
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        # Save new access token to .env
        save_to_env('current_access_token', access_token)
        
        return access_token
    else:
        print(f"Error refreshing access token: {response.status_code}")
        print(response.text)
        return None

def test_access_token(access_token):
    """Test if the access token is valid by making a team API call"""
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    # Test with team endpoint
    team_response = requests.post('https://api.dropboxapi.com/2/team/get_info', headers=headers)
    
    if team_response.status_code == 200:
        team_data = team_response.json()
        print(f"Token is valid. Connected to team: {team_data.get('name', 'Unknown team')}")
        return True
    else:
        print(f"Team token validation failed: {team_response.status_code}")
        print(team_response.text)
        return False

if __name__ == "__main__":
    # Load current environment
    env_vars = load_env()
    current_token = env_vars['current_access_token']
    
    # Try to use existing token first
    if current_token and test_access_token(current_token):
        print("Using existing valid access token.")
    else:
        # Token doesn't exist or is invalid, get a new one
        print("Current access token is invalid or missing. Getting a new one...")
        access_token = get_access_token()
        
        if access_token:
            test_access_token(access_token) 