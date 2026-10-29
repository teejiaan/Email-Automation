import queue
import sqlite3
import threading
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from batch_sender import send_batches
from send_log import SendLog


class BatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_folder = TemporaryDirectory()
        self.addCleanup(self.temp_folder.cleanup)

        folder = Path(self.temp_folder.name)
        self.database = folder / "test.sqlite3"
        self.log = SendLog(self.database)

        self.jobs = []

        for name in ("John", "Jane"):
            certificate = folder / f"{name}.pdf"
            certificate.write_bytes(b"Test attachment placeholder")

            self.jobs.append({
                "name": name,
                "recipient": f"{name.lower()}@example.com",
                "subject": "Your certificate",
                "body": f"Dear {name}",
                "certificate_path": str(certificate),
            })

    def run_batch(self, sender):
        events = queue.Queue()

        # Replace both the real sender and the normal log location.
        with (
            patch("batch_sender.SendLog", return_value=self.log),
            patch(
                "batch_sender.send_certificate_email",
                side_effect=sender,
            ) as mocked_sender,
        ):
            send_batches(
                service=object(),
                jobs=self.jobs,
                progress_queue=events,
                stop_event=threading.Event(),
                batch_size=2,
                message_delay=0,
                batch_pause=0,
                dry_run=False,
                campaign_id="integration-test",
            )

        collected = []

        while not events.empty():
            collected.append(events.get_nowait())

        return mocked_sender, collected

    def read_records(self):
        connection = sqlite3.connect(self.database)

        try:
            return connection.execute(
                """
                SELECT recipient, status, message_id
                FROM sends
                ORDER BY recipient
                """
            ).fetchall()
        finally:
            connection.close()

    @staticmethod
    def fake_success(service, recipient, subject, body, path):
        return f"fake-id-{recipient}"

    def test_success_is_logged_and_repeat_is_skipped(self):
        sender, events = self.run_batch(self.fake_success)

        self.assertEqual(sender.call_count, 2)
        self.assertEqual(events[-1]["reason"], "completed")

        self.assertEqual(
            self.read_records(),
            [
                (
                    "jane@example.com",
                    "sent",
                    "fake-id-jane@example.com",
                ),
                (
                    "john@example.com",
                    "sent",
                    "fake-id-john@example.com",
                ),
            ],
        )

        # Reopen the database to simulate a later application session.
        self.log = SendLog(self.database)

        sender, events = self.run_batch(self.fake_success)

        sender.assert_not_called()
        self.assertEqual(
            sum(event["type"] == "skipped" for event in events),
            2,
        )

    def test_timeout_stops_and_blocks_retry(self):
        def timeout(*args):
            raise TimeoutError("Simulated network timeout")

        sender, events = self.run_batch(timeout)

        self.assertEqual(sender.call_count, 1)
        self.assertEqual(events[-1]["reason"], "review_required")
        self.assertEqual(
            self.read_records(),
            [("john@example.com", "unconfirmed", None)],
        )

        sender, events = self.run_batch(self.fake_success)

        sender.assert_not_called()
        self.assertEqual(events[-1]["reason"], "review_required")

    def test_initial_log_failure_prevents_sending(self):
        with patch.object(
            self.log,
            "claim",
            side_effect=OSError("Simulated database failure"),
        ):
            sender, events = self.run_batch(self.fake_success)

        sender.assert_not_called()
        self.assertEqual(events[-1]["reason"], "review_required")

    def test_success_log_failure_blocks_resending(self):
        with patch.object(
            self.log,
            "record",
            side_effect=OSError("Simulated write failure"),
        ):
            sender, events = self.run_batch(self.fake_success)

        self.assertEqual(sender.call_count, 1)
        self.assertEqual(events[-1]["reason"], "review_required")
        self.assertEqual(
            self.read_records(),
            [("john@example.com", "sending", None)],
        )

        sender, events = self.run_batch(self.fake_success)

        sender.assert_not_called()
        self.assertEqual(events[-1]["reason"], "review_required")

    def test_missing_pdf_prevents_sending(self):
        Path(self.jobs[0]["certificate_path"]).unlink()

        sender, events = self.run_batch(self.fake_success)

        sender.assert_not_called()
        self.assertEqual(events[-1]["reason"], "error")
        self.assertEqual(self.read_records(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)