import queue
import threading
from tempfile import TemporaryDirectory
from pathlib import Path

from batch_sender import prepare_email_jobs, send_batches


def main():
    with TemporaryDirectory() as folder:
        participants = []

        for name, email in (
            ("John Tan", "john@example.com"),
            ("Jane Lim", "jane@example.com"),
            ("Alex Lee", "alex@example.com"),
        ):
            certificate = Path(folder) / f"{name}.pdf"

            # Placeholder file for dry-run testing only.
            certificate.write_bytes(b"Dry-run placeholder")

            participants.append({
                "name": name,
                "email": email,
                "certificate": str(certificate),
            })

        template = {
            "subject": "Certificate for [Name]",
            "body": "Dear [Name],\n\nYour certificate is attached.",
            "signature": "Best regards,\nEvents Team",
        }

        jobs = prepare_email_jobs(participants, template)

        progress_queue = queue.Queue()
        stop_event = threading.Event()

        send_batches(
            service=None,
            jobs=jobs,
            progress_queue=progress_queue,
            stop_event=stop_event,
            batch_size=2,
            message_delay=0,
            batch_pause=0,
            dry_run=True,
        )

        while not progress_queue.empty():
            print(progress_queue.get_nowait())


if __name__ == "__main__":
    main()