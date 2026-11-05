import os
import base64
from email.message import EmailMessage
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
]

CONFIG_DIR = (
    Path(os.environ["LOCALAPPDATA"])
    / "CertificateEmailAutomation"
)

CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"


def oauth_config_path():
    """Use a local override or the desktop client shipped with the executable."""
    bundled = Path(__file__).resolve().parent / 'oauth' / 'credentials.json'
    if CREDENTIALS_FILE.is_file():
        return CREDENTIALS_FILE
    if bundled.is_file():
        return bundled
    raise FileNotFoundError(
        'Google OAuth configuration is missing. Re-extract the complete application ZIP '
        f'or place a Desktop client configuration at {CREDENTIALS_FILE}.')


def load_credentials(interactive=True, choose_account=False):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    credentials = None

    # Reuse a previously authorised account.
    if TOKEN_FILE.exists() and not choose_account:
        try:
            credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE))
        except ValueError:
            credentials = None
        if credentials and not credentials.has_scopes(SCOPES):
            credentials = None

    # Refresh an expired login where possible.
    if (
        credentials
        and credentials.expired
        and credentials.refresh_token
    ):
        try:
            credentials.refresh(Request())
        except RefreshError:
            credentials = None

    # Otherwise, open Google's browser sign-in.
    if not credentials or not credentials.valid:
        if not interactive:
            return None
        configuration = oauth_config_path()

        flow = InstalledAppFlow.from_client_secrets_file(
            str(configuration),
            SCOPES,
        )

        credentials = flow.run_local_server(
            port=0,
            timeout_seconds=180,
            prompt="select_account",
        )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    return credentials


def connect_gmail():
    credentials = load_credentials()
    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )

def send_certificate_email(
    service,
    recipient,
    subject,
    body,
    certificate_path,
):
    attachment = Path(certificate_path)

    if not attachment.is_file():
        raise FileNotFoundError(f"Certificate not found: {attachment}")

    if attachment.suffix.lower() != ".pdf":
        raise ValueError("The certificate must be a PDF.")

    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    message.add_attachment(
        attachment.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=attachment.name,
    )

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("ascii")

    result = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={"raw": encoded_message},
        )
        .execute(num_retries=0)
    )

    return result["id"]


if __name__ == "__main__":
    service = connect_gmail()
    print("Gmail authorisation completed. No email has been sent.")
