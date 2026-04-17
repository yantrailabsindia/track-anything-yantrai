"""
Desktop Agent Authentication — handles login and token storage
"""
import json
import requests
from pathlib import Path
from desktop.config import API_URL, DATA_DIR

AUTH_FILE = DATA_DIR / "auth.json"

def load_auth_token():
    """Load saved auth token from disk"""
    if AUTH_FILE.exists():
        try:
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
                return data.get('token'), data.get('user_id'), data.get('username'), data.get('server_url')
        except Exception as e:
            print(f"Error loading auth: {e}")
    return None, None, None, None

def save_auth_token(token, user_id, username, org_name=None, server_url=None):
    """Save auth token to disk"""
    try:
        # Load existing data if file exists to preserve extra fields if any
        auth_data = {}
        if AUTH_FILE.exists():
            try:
                with open(AUTH_FILE, 'r') as f:
                    auth_data = json.load(f)
            except:
                pass
        
        auth_data.update({
            'token': token,
            'user_id': user_id,
            'username': username
        })
        if org_name:
            auth_data['org_name'] = org_name
        if server_url:
            auth_data['server_url'] = server_url
            
        with open(AUTH_FILE, 'w') as f:
            json.dump(auth_data, f, indent=4)
        print(f"Saved auth for user: {username} on {server_url or 'default server'}")
    except Exception as e:
        print(f"Error saving auth: {e}")

def login(username: str, password: str, server_url: str = None) -> tuple:
    """
    Authenticate with backend
    Returns: (token, user_id, username) or (None, None, None) on failure
    """
    base_url = server_url or API_URL
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            # Backend returns 'token' not 'access_token'
            token = data.get('token')
            user_data = data.get('user', {})
            user_id = user_data.get('id') if isinstance(user_data, dict) else getattr(user_data, 'id', None)

            # Extract org_name if available
            org_name = None
            if isinstance(user_data, dict):
                org_data = user_data.get('organization', {})
                if isinstance(org_data, dict):
                    org_name = org_data.get('name')

            if token and user_id:
                save_auth_token(token, user_id, username, org_name=org_name, server_url=server_url)
                return token, user_id, username
            else:
                print(f"Login response missing token or user_id: {data}")
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Login error: {e}")
    return None, None, None

def is_authenticated():
    """Check if we have a valid token"""
    token, _, _, _ = load_auth_token()
    return token is not None

def verify_password(username: str, password: str, server_url: str = None) -> bool:
    """
    Verify password by calling backend endpoint
    Does NOT require a valid token — uses username/password directly
    Returns: True if password is correct, False otherwise
    """
    base_url = server_url or API_URL
    try:
        response = requests.post(
            f"{base_url}/api/auth/verify-password",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('valid', False)
        else:
            print(f"Password verification failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def logout():
    """
    Log out current user:
    - Delete auth.json file
    - Clear cached credentials
    Returns: True if successful, False otherwise
    """
    try:
        if AUTH_FILE.exists():
            AUTH_FILE.unlink()
            print("Auth file deleted, user logged out")
        return True
    except Exception as e:
        print(f"Error during logout: {e}")
        return False
