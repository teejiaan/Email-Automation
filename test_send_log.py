from pathlib import Path
from tempfile import TemporaryDirectory

from send_log import SendLog


def main():
    with TemporaryDirectory() as folder:
        folder = Path(folder)
        certificate = folder / "example.pdf"
        certificate.write_bytes(b"Test placeholder")

        database = folder / "test.sqlite3"

        job = {
            "recipient": "example@example.com",
            "subject": "Test certificate",
            "body": "Dear Example",
            "certificate_path": str(certificate),
        }

        log = SendLog(database)

        assert log.claim("test-campaign", job) is True

        # Simulate restarting with an unfinished sending attempt.
        reopened = SendLog(database)

        try:
            reopened.claim("test-campaign", job)
        except ValueError:
            print("PASS: unfinished attempt blocks automatic resending")
        else:
            raise AssertionError("Unfinished attempt was not blocked")

        # Simulate a confirmed Gmail response in this temporary test log.
        log.record(
            "test-campaign",
            job["recipient"],
            "sent",
            message_id="fake-test-message-id",
        )

        assert reopened.claim("test-campaign", job) is False
        print("PASS: confirmed send is skipped after reopening")

        changed_job = dict(job, subject="Changed subject")

        try:
            reopened.claim("test-campaign", changed_job)
        except ValueError:
            print("PASS: changed message requires review")
        else:
            raise AssertionError("Changed message was not blocked")


if __name__ == "__main__":
    main()