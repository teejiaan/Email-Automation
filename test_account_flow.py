"""Account lifecycle tests: no browser, token modification or Gmail requests."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import gmail_service
import account_service
from send_log import SendLog


class AccountTests(unittest.TestCase):
    def test_old_send_only_token_requires_new_consent(self):
        credentials = MagicMock()
        credentials.has_scopes.return_value = False
        with patch.object(gmail_service, 'CONFIG_DIR') as directory, \
             patch.object(gmail_service, 'TOKEN_FILE') as token, \
             patch.object(gmail_service.Credentials, 'from_authorized_user_file', return_value=credentials), \
             patch.object(gmail_service.InstalledAppFlow, 'from_client_secrets_file') as flow:
            token.exists.return_value = True
            self.assertIsNone(gmail_service.load_credentials(interactive=False))
            flow.assert_not_called()

    def test_profile_fallback_without_photo_or_name(self):
        response = MagicMock()
        response.json.return_value = {'sub': 'account-a', 'email': 'a@example.com'}
        session = MagicMock()
        session.__enter__.return_value.get.return_value = response
        with patch.object(account_service, 'load_credentials', return_value=object()), \
             patch.object(account_service, 'AuthorizedSession', return_value=session):
            account = account_service.connect_account()
        self.assertEqual(account.name, 'a@example.com')
        self.assertIsNone(account.picture)

    def test_logout_only_removes_token(self):
        with tempfile.TemporaryDirectory() as folder:
            token = Path(folder) / 'token.json'
            log = Path(folder) / 'send_log.sqlite3'
            token.write_text('test')
            log.write_text('keep')
            with patch.object(account_service, 'TOKEN_FILE', token):
                account_service.logout_account()
            self.assertFalse(token.exists())
            self.assertEqual(log.read_text(), 'keep')

    def test_accounts_have_separate_history_and_legacy_is_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = Path(folder) / 'certificate.pdf'
            pdf.write_bytes(b'placeholder')
            path = Path(folder) / 'log.sqlite3'
            job = {'recipient': 'recipient@example.com', 'subject': 'Subject',
                   'body': 'Body', 'certificate_path': str(pdf)}
            a, b = SendLog(path, 'a'), SendLog(path, 'b')
            self.assertTrue(a.claim('event', job))
            a.record('event', job['recipient'], 'sent', message_id='a-id')
            self.assertFalse(a.claim('event', job))
            self.assertTrue(b.claim('event', job))
            legacy = SendLog(path)
            legacy.claim('old-event', job)
            legacy.record('old-event', job['recipient'], 'sent', message_id='legacy')
            with self.assertRaisesRegex(ValueError, 'older send history'):
                a.claim('old-event', job)


if __name__ == '__main__':
    unittest.main(verbosity=2)
