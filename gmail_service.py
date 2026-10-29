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
    "https://www.googleapis.com/auth/gmail.send",
]

CONFIG_DIR = (
    Path(os.environ["LOCALAPPDATA"])
    / "CertificateEmailAutomation"
)

CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"


def connect_gmail():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    credentials = None

    # Reuse a previously authorised account.
    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

        if not credentials.has_scopes(SCOPES):
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
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                "Google OAuth configuration was not found at:\n"
                f"{CREDENTIALS_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES,
        )

        credentials = flow.run_local_server(
            port=0,
            timeout_seconds=180,
        )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

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