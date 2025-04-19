# Dropbox Token Manager

A Python utility to manage Dropbox access and refresh tokens, automating the OAuth flow and token refreshing process.

## Features

- Automatically opens authorization URL in browser
- Guides user through OAuth flow to obtain refresh and access tokens
- Saves tokens to `.env` file
- Validates tokens with Dropbox API
- Handles both individual and Dropbox Business team accounts
- Auto-refreshes expired access tokens using refresh token

## Prerequisites

- Python 3.x
- A Dropbox API app (create one at https://www.dropbox.com/developers/apps)
- App key and secret from your Dropbox app

## Setup

1. Create a `.env` file in the same directory with your Dropbox app credentials:

```
app_key=YOUR_APP_KEY
app_secret=YOUR_APP_SECRET
```

2. Install dependencies:

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install python-dotenv requests
```

## Usage

Run the script:

```bash
python dropbox_token_manager.py
```

On first run, it will:
1. Open your browser for authorization
2. Ask you to input the authorization code
3. Get and save both refresh and access tokens
4. Validate the token

On subsequent runs, it will:
1. Check if the current access token is valid
2. If invalid or expired, automatically refresh it using the saved refresh token
3. Update the `.env` file with the new access token

## Notes

- Refresh tokens don't expire unless revoked
- Access tokens typically expire after a few hours (usually 4 hours)
- The utility handles both individual Dropbox accounts and Dropbox Business team accounts

Based on information from [Dropbox Forum](https://www.dropboxforum.com/discussions/101000014/get-refresh-token-from-access-token/596739). 