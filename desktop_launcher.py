"""Desktop entry point, with an offline packaged startup check."""
import sys
from pathlib import Path
import customtkinter as ctk
from app import MailerApp

if __name__ == '__main__':
    ctk.set_appearance_mode('light')
    offline = len(sys.argv) == 3 and sys.argv[1] == '--offline-check'
    app = MailerApp(restore_session=not offline)
    if offline:
        def finish():
            from gmail_service import oauth_config_path, SCOPES
            from google_auth_oauthlib.flow import InstalledAppFlow
            configuration = oauth_config_path()
            InstalledAppFlow.from_client_secrets_file(str(configuration), SCOPES)
            Path(sys.argv[2]).write_text('Packaged UI and Desktop OAuth configuration loaded successfully.', encoding='utf-8')
            app.destroy()
        app.after(500, finish)
    app.mainloop()
