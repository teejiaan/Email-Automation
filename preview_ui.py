"""Local visual QA with a fictional account. No authentication or sends."""
import time
from pathlib import Path
from PIL import ImageGrab
import customtkinter as ctk
from app import MailerApp
from account_service import GoogleAccount


def capture(app, name):
    app.update()
    time.sleep(0.4)
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(name)


if __name__ == '__main__':
    ctk.set_appearance_mode('light')
    app = MailerApp(restore_session=False)
    try:
        app.geometry('1180x880+40+40')
        app.lift()
        capture(app, 'account-page.png')
        app.apply_account(GoogleAccount(None, 'fictional', 'daren@example.com', 'Daren Tee'))
        app.show_workspace()
        app.subject_entry.insert(0, 'Your workshop certificate')
        app.excel_label.configure(text='Workshop participants.xlsx')
        app.cert_label.configure(text='Workshop certificates')
        app.match_status.configure(text='3 matched · 0 need review')
        app.put_text(app.preview_box,
            'To: alex@example.com\nSubject: Your workshop certificate\n\n'
            'Dear Alex,\n\nThank you for joining our workshop. Please find your '
            'certificate attached.\n\nBest regards,\nEvents Team\n\nAttachment: Alex.pdf', True)
        app.preview_count.configure(text='1 of 3')
        capture(app, 'workspace-page.png')
        app.toggle_account_menu()
        capture(app, 'account-menu.png')
        app.hide_account_menu()
        app.geometry('900x680+40+40')
        capture(app, 'workspace-small.png')
    finally:
        app.destroy()
