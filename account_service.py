"""Google identity and local session lifecycle, independent of the GUI."""
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from google.auth.transport.requests import AuthorizedSession
from googleapiclient.discovery import build

from gmail_service import load_credentials, TOKEN_FILE


@dataclass
class GoogleAccount:
    credentials: object
    subject: str
    email: str
    name: str
    picture: bytes | None = None

    def gmail_client(self):
        # Each worker gets its own HTTP transport.
        return build('gmail', 'v1', credentials=self.credentials,
                     cache_discovery=False)


def connect_account(interactive=True, choose_account=False):
    credentials = load_credentials(interactive, choose_account)
    if credentials is None:
        return None
    with AuthorizedSession(credentials) as session:
        response = session.get(
            'https://openidconnect.googleapis.com/v1/userinfo', timeout=20)
        response.raise_for_status()
        profile = response.json()
    if not profile.get('sub') or not profile.get('email'):
        raise ValueError('Google did not return an account ID and email address.')
    picture = None
    url = profile.get('picture', '')
    # Fetch public avatars without forwarding the OAuth bearer token.
    parsed = urlparse(url)
    if parsed.scheme == 'https' and (parsed.hostname or '').endswith('.googleusercontent.com'):
        try:
            with requests.get(url, timeout=8, stream=True) as image_response:
                image_response.raise_for_status()
                data = bytearray()
                for chunk in image_response.iter_content(16384):
                    data.extend(chunk)
                    if len(data) > 2_000_000:
                        raise ValueError('Avatar is too large.')
                picture = bytes(data)
        except (requests.RequestException, ValueError) as error:
            print(f"Could not download profile picture: {error}")
    return GoogleAccount(credentials, profile['sub'], profile['email'],
                         profile.get('name') or profile['email'], picture)


def logout_account():
    """Forget this app's login; leave templates, logs and browser sessions alone."""
    TOKEN_FILE.unlink(missing_ok=True)
