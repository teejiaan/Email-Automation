"""Offline widget-level checks. No real account or email is used."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk
from account_service import GoogleAccount
from app import MailerApp


class UIFlowTests(unittest.TestCase):
    def setUp(self):
        ctk.set_appearance_mode('light')
        self.app = MailerApp(restore_session=False)
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.account = GoogleAccount(None, 'fake-google-id', 'test@example.com', 'Test User')

    def pump_until_idle(self):
        deadline = time.monotonic() + 5
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.02)
        self.assertFalse(self.app.busy)

    def test_navigation_menu_logout_and_busy_guard(self):
        self.app.apply_account(self.account)
        self.app.show_workspace()
        self.app.toggle_account_menu()
        self.assertIsNotNone(self.app.account_menu)
        self.assertEqual(self.app.account_email.cget('text'), 'test@example.com')
        self.app.set_busy(True, 'batch')
        with patch('app.logout_account') as logout:
            self.app.logout()
            logout.assert_not_called()
            self.app.set_busy(False)
            self.app.logout()
            logout.assert_called_once()
        self.assertIsNone(self.app.account)
        self.assertFalse(self.app.matched)

    def test_match_preview_dry_run_and_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = Path(folder) / 'Test User.pdf'
            pdf.write_bytes(b'placeholder')
            self.app.apply_account(self.account)
            self.app.excel_path = 'mock.xlsx'
            self.app.certificate_folder = folder
            with patch('app.read_participants', return_value=[
                {'name': 'Test User', 'email': 'test@example.com'}
            ]):
                self.app.match()
            self.assertTrue(self.app.matched)
            self.app.subject_entry.insert(0, 'Certificate for [Name]')
            self.app.preview()
            self.assertIn('Dear Test User', self.app.preview_box.get('1.0', 'end'))
            jobs = self.app.jobs()
            with patch('batch_sender.send_certificate_email') as sender:
                self.app.launch_batch(jobs, 'test', True)
                self.pump_until_idle()
                sender.assert_not_called()
                self.assertIn('[SIMULATED]', self.app.log_box.get('1.0', 'end'))
                self.app.launch_batch(jobs * 3, 'test', True)
                self.app.stop()
                self.pump_until_idle()
                sender.assert_not_called()
                self.assertIn('stopped', self.app.status.cget('text'))

    def test_ambiguous_certificates_are_not_selected(self):
        with tempfile.TemporaryDirectory() as folder:
            for filename in ('Test User.pdf', 'Test_User.pdf'):
                (Path(folder) / filename).write_bytes(b'placeholder')
            self.app.excel_path = 'mock.xlsx'
            self.app.certificate_folder = folder
            with patch('app.read_participants', return_value=[
                {'name': 'Test User', 'email': 'test@example.com'}
            ]):
                self.app.match()
            self.assertIsNone(self.app.participants[0]['certificate'])
            self.assertIn('multiple matching PDFs', self.app.log_box.get('1.0', 'end'))

    def test_completion_popup_only_for_successful_real_campaign(self):
        with patch.object(self.app, 'show_completion') as popup:
            for reason, dry_run in [('completed', True), ('stopped', False),
                                    ('review_required', False)]:
                self.app.events.put({'type': 'finished', 'reason': reason,
                                     'dry_run': dry_run, 'processed': 1, 'total': 3})
                self.app.poll_events()
            popup.assert_not_called()
            self.app.events.put({'type': 'finished', 'reason': 'completed',
                                 'dry_run': False, 'processed': 3, 'total': 3})
            self.app.poll_events()
            popup.assert_called_once()

    def test_reset_keeps_account_and_activity_but_clears_mailing(self):
        self.app.apply_account(self.account)
        self.app.excel_path = 'old.xlsx'
        self.app.certificate_folder = 'old-certificates'
        self.app.participants = [{'name': 'Old recipient'}]
        self.app.matched = True
        self.app.campaign_entry.insert(0, 'old-campaign')
        self.app.subject_entry.insert(0, 'Old subject')
        self.app.log('Previous campaign completed')
        self.app.progress.set(1)
        self.app.reset_mailing()
        self.assertIs(self.app.account, self.account)
        self.assertFalse(self.app.matched)
        self.assertEqual(self.app.participants, [])
        self.assertEqual(self.app.excel_path, '')
        self.assertEqual(self.app.campaign_entry.get(), '')
        self.assertEqual(self.app.subject_entry.get(), '')
        self.assertEqual(self.app.progress.get(), 0)
        self.assertIn('Previous campaign completed', self.app.log_box.get('1.0', 'end'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
