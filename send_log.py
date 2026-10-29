import hashlib
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


LOG_PATH = (
    Path(os.environ["LOCALAPPDATA"])
    / "CertificateEmailAutomation"
    / "send_log.sqlite3"
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def job_fingerprint(job):
    """Identify the exact message and attachment contents."""
    attachment = Path(job["certificate_path"])

    contents = {
        "recipient": job["recipient"],
        "subject": job["subject"],
        "body": job["body"],
        "attachment_name": attachment.name,
        "attachment_hash": hashlib.sha256(
            attachment.read_bytes()
        ).hexdigest(),
    }

    encoded = json.dumps(
        contents,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


class SendLog:
    def __init__(self, path=LOG_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with closing(self.connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS sends (
                        campaign_id TEXT NOT NULL,
                        recipient TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message_id TEXT,
                        error TEXT,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (campaign_id, recipient)
                    )
                """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def claim(self, campaign_id, job):
        """Return False for a confirmed previous send.

        Otherwise record an attempt, or block an uncertain/changed job.
        """
        if not campaign_id.strip():
            raise ValueError("A campaign ID is required.")

        recipient = job["recipient"].strip().casefold()
        fingerprint = job_fingerprint(job)

        with closing(self.connect()) as connection:
            with connection:
                # Prevent two workers claiming the same recipient together.
                connection.execute("BEGIN IMMEDIATE")

                previous = connection.execute(
                    """
                    SELECT fingerprint, status
                    FROM sends
                    WHERE campaign_id = ? AND recipient = ?
                    """,
                    (campaign_id, recipient),
                ).fetchone()

                if previous:
                    previous_fingerprint, status = previous

                    if previous_fingerprint != fingerprint:
                        raise ValueError(
                            f"{recipient}: the message or attachment changed "
                            "since its previous attempt. Review before sending."
                        )

                    if status == "sent":
                        return False

                    raise ValueError(
                        f"{recipient}: previous status is '{status}'. "
                        "Check Gmail's Sent folder before retrying."
                    )

                connection.execute(
                    """
                    INSERT INTO sends (
                        campaign_id, recipient, fingerprint,
                        status, updated_at
                    )
                    VALUES (?, ?, ?, 'sending', ?)
                    """,
                    (
                        campaign_id,
                        recipient,
                        fingerprint,
                        utc_now(),
                    ),
                )

        return True

    def record(self, campaign_id, recipient, status,
               message_id=None, error=None):
        if status not in ("sent", "unconfirmed"):
            raise ValueError("Invalid send-log status.")

        if status == "sent" and not message_id:
            raise ValueError("A sent entry requires a Gmail message ID.")

        with closing(self.connect()) as connection:
            with connection:
                result = connection.execute(
                    """
                    UPDATE sends
                    SET status = ?, message_id = ?,
                        error = ?, updated_at = ?
                    WHERE campaign_id = ? AND recipient = ?
                      AND status = 'sending'
                    """,
                    (
                        status,
                        message_id,
                        error,
                        utc_now(),
                        campaign_id,
                        recipient.strip().casefold(),
                    ),
                )

                if result.rowcount != 1:
                    raise RuntimeError(
                        "Could not update the recorded sending attempt."
                    )