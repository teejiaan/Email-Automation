import queue
import threading
from io import BytesIO
from pathlib import Path
from tkinter import Canvas, filedialog, messagebox, simpledialog

import customtkinter as ctk

from account_service import connect_account, logout_account
from history_view import FONT_FAMILY, HistoryWindow
from batch_sender import prepare_email_jobs, send_batches
from certificate_matcher import get_certificates, normalize_name
from email_templates import personalise_template, save_template, load_template
from excel_reader import read_participants
from gmail_service import send_certificate_email

BG = '#F3F5F8'
CARD = '#FFFFFF'
INK = '#17243A'
MUTED = '#65738A'
ACCENT = '#355FE5'
BORDER = '#E3E8F0'



class AvatarIcon(Canvas):
    """A profile image above a separate circular hover halo."""

    def __init__(self, parent, background, command=None):
        super().__init__(parent, width=50, height=50, bg=background,
                         highlightthickness=0, borderwidth=0,
                         cursor='hand2' if command else '')
        self._photo = None
        self._halo = self.create_oval(
            1, 1, 49, 49, fill='#DCBAFC', outline='', state='hidden')
        self._picture = self.create_image(25, 25)
        self._initial = self.create_text(
            25, 25, text='G', fill=INK, font=(FONT_FAMILY, 22, 'bold'))
        self.bind('<Enter>', lambda event: self.itemconfigure(self._halo, state='normal'))
        self.bind('<Leave>', lambda event: self.itemconfigure(self._halo, state='hidden'))
        if command:
            self.bind('<ButtonRelease-1>', lambda event: command())

    def set_profile(self, photo=None, initial='G'):
        from PIL import Image, ImageTk

        self._photo = (
            ImageTk.PhotoImage(photo.resize((44, 44), Image.Resampling.LANCZOS), master=self)
            if photo is not None else None
        )
        self.itemconfigure(self._picture, image=self._photo or '')
        self.itemconfigure(self._initial, text='' if self._photo else initial)
        self.itemconfigure(self._halo, state='hidden')


class MailerApp(ctk.CTk):
    def __init__(self, restore_session=True):
        super().__init__()
        self.title('GMass Clone - A Certificate Batch Email Sender App')
        self.geometry('1180x880')
        self.minsize(900, 680)
        self.configure(fg_color=BG)
        self.account = None
        self.busy = False
        self.operation = None
        self.excel_path = ''
        self.certificate_folder = ''
        self.participants = []
        self.matched = False
        self.preview_index = 0
        self.preview_people = []
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.controls = []
        self.profile_image = None
        self.history_window = None
        self.account_menu = None
        self.log_visible = False
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.account_page = ctk.CTkFrame(self, fg_color=BG)
        self.workspace = ctk.CTkFrame(self, fg_color=BG)
        for page in (self.account_page, self.workspace):
            page.grid(row=0, column=0, sticky='nsew')
        self.build_account_page()
        self.build_workspace()
        self.account_page.tkraise()
        self.protocol('WM_DELETE_WINDOW', self.close_app)
        self.bind('<Escape>', lambda _event: self.hide_account_menu())
        self.bind('<Button-1>', self.dismiss_menu, add='+')
        self.after(100, self.poll_events)
        if restore_session:
            self.after(150, lambda: self.connect(interactive=False))

    def label(self, parent, text, size=13, bold=False, **kwargs):
        return ctk.CTkLabel(parent, text=text, text_color=INK,
                           font=ctk.CTkFont(
                               family=FONT_FAMILY, size=size, weight='bold' if bold else 'normal'),
                           **kwargs)

    def button(self, parent, text, command, primary=False, register=True, **kwargs):
        button = ctk.CTkButton(
            parent, text=text, command=command, height=38, corner_radius=10,
            font=ctk.CTkFont(
                family=FONT_FAMILY,
                size=14,
                weight='bold',
            ),
            fg_color=ACCENT if primary else '#EDF1FA',
            hover_color='#294CC0' if primary else '#DFE6F5',
            text_color='white' if primary else INK, **kwargs)
        if register:
            self.controls.append(button)
        return button

    def entry(self, parent, placeholder):
        widget = ctk.CTkEntry(parent, placeholder_text=placeholder, height=38,
                              font=ctk.CTkFont(
                                family=FONT_FAMILY,
                                size=14,
                            ),
                             fg_color=CARD, text_color=INK, border_color=BORDER,
                             corner_radius=9)
        self.controls.append(widget)
        return widget
    
    def scroll_workspace(self, event):
        if event.delta:
            direction = -1 if event.delta > 0 else 1

            self.workspace_scroll._parent_canvas.yview_scroll(
                direction * 15,
                "units",
            )

        return "break"

    def handle_textbox_scroll(self, event, textbox):
        if self.focus_get() == textbox._textbox:
            # Let the focused textbox handle scrolling normally.
            return None

        # Otherwise, scroll the main page.
        return self.scroll_workspace(event)

    def textbox(self, parent, height, editable=True):
        widget = ctk.CTkTextbox(parent, height=height, wrap='word',
                                font=ctk.CTkFont(
                                    family=FONT_FAMILY,
                                    size=14,
                                ),
                                fg_color='#F8FAFD', text_color=INK,
                                border_color=BORDER, border_width=1, corner_radius=10)
        if editable:
            self.controls.append(widget)
        else:
            widget.configure(state='disabled')
        return widget

    @staticmethod
    def put_text(widget, text, readonly=False):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        if readonly:
            widget.configure(state='disabled')

    def build_account_page(self):
        self.account_page.grid_rowconfigure((0, 2), weight=1)
        self.account_page.grid_columnconfigure((0, 2), weight=1)
        shadow = ctk.CTkFrame(self.account_page, fg_color='#E6EBF3', corner_radius=26)
        shadow.grid(row=1, column=1, padx=30, pady=30)
        card = ctk.CTkFrame(shadow, fg_color=CARD, corner_radius=24, width=470)
        card.pack(padx=(0, 3), pady=(0, 5), fill='both')
        self.label(card, 'CERTIFICATE MAILER', 12, True).pack(pady=(38, 12))
        self.label(card, 'A personal touch.\nEvery certificate.', 30, True).pack(padx=40)
        self.label(card, 'Choose the Google account you want to send from.',
                   wraplength=360).pack(padx=40, pady=(14, 26))
        self.account_avatar = AvatarIcon(card, CARD)
        self.account_avatar.pack(pady=(0, 10))
        self.account_name = self.label(card, 'Connect your account', 17, True)
        self.account_name.pack()
        self.account_email = self.label(card, 'Sign in securely in your browser.')
        self.account_email.pack(padx=30, pady=(4, 20))
        self.connect_button = self.button(card, 'Connect with Google', self.connect,
                                          primary=True, register=False, width=330)
        self.connect_button.pack(padx=40, pady=5)
        self.continue_button = self.button(card, 'Continue to workspace', self.show_workspace,
                                           primary=True, register=False, width=330)
        self.switch_button = self.button(card, 'Use another account',
                                         lambda: self.connect(choose_account=True),
                                         register=False, width=330)
        self.auth_status = self.label(card, '', wraplength=350)
        self.auth_status.pack(padx=35, pady=(16, 12))
        self.button(card, 'Quit', self.close_app, register=False, width=90).pack(pady=(0, 24))

    def build_workspace(self):
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self.workspace, fg_color=BG, height=70)
        header.grid(row=0, column=0, sticky='ew', padx=32, pady=(14, 4))
        header.grid_columnconfigure(1, weight=1)
        self.label(header, 'Certificate Mailer', 21, True).grid(row=0, column=0, sticky='w')
        self.sender_label = self.label(header, '')
        self.sender_label.grid(row=0, column=1, sticky='e', padx=16)
        self.avatar_button = AvatarIcon(header, BG, self.toggle_account_menu)
        self.avatar_button.grid(row=0, column=2)

        scroll = ctk.CTkScrollableFrame(self.workspace, fg_color=BG, corner_radius=0)
        self.workspace_scroll = scroll
        scroll.grid(row=1, column=0, sticky='nsew')
        scroll.grid_columnconfigure((0, 2), weight=1)
        scroll.grid_columnconfigure(1, weight=8)
        self.main_card = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=22,
                                     border_width=1, border_color=BORDER)
        self.main_card.grid(row=0, column=1, sticky='ew', padx=16, pady=(14, 26))
        self.main_card.grid_columnconfigure((0, 1), weight=1, uniform='content')
        self.label(self.main_card, 'New mailing', 35, True).grid(
            row=0, column=0, columnspan=2, sticky='w', padx=26, pady=(24, 4))
        self.label(self.main_card, 'Match your files, compose a message, then review.').grid(
            row=1, column=0, columnspan=2, sticky='w', padx=26, pady=(0, 20))
        self.campaign_entry = self.entry(self.main_card, 'Campaign name, e.g. workshop-november-2026')
        self.campaign_entry.grid(row=2, column=0, columnspan=2, sticky='ew', padx=26)

        files = ctk.CTkFrame(self.main_card, fg_color='#F7F9FC', corner_radius=14)
        files.grid(row=3, column=0, columnspan=2, sticky='ew', padx=26, pady=20)
        files.grid_columnconfigure((0, 1), weight=1, uniform='files')
        self.label(files, '01   Recipients & certificates', 20, True).grid(
            row=0, column=0, columnspan=2, sticky='w', padx=16, pady=(15, 10))
        excel_button = self.button(
            files,
            'Choose Excel',
            self.choose_excel,
        )

        excel_button.configure(
            fg_color='#15803D',       # Green background
            hover_color='#166534',    # Darker green on hover
            text_color='white',
        )

        excel_button.grid(
            row=1,
            column=0,
            sticky='ew',
            padx=(16, 8),
        )
        
        certificates_button = self.button(
            files,
            'Choose certificates',
            self.choose_certificates,
        )

        certificates_button.configure(
            fg_color='#1D4F6B',       # Blue background
            hover_color='#1A3F5B',    # Darker blue on hover
            text_color='white',
        )

        certificates_button.grid(
            row=1,
            column=1,
            sticky='ew',
            padx=(8, 16),
        )

        self.excel_label = self.label(files, 'No spreadsheet selected', wraplength=300)
        self.excel_label.grid(row=2, column=0, padx=16, pady=8)
        self.cert_label = self.label(files, 'No folder selected', wraplength=300)
        self.cert_label.grid(row=2, column=1, padx=16, pady=8)
        
        check_frame = ctk.CTkFrame(files, fg_color='transparent')
        check_frame.grid(
            row=4,
            column=0,
            columnspan=2,
            pady=(0, 14),
        )
        check_button = self.button(
            check_frame,
            'Check matches',
            self.match,
        )

        check_button.configure(
            fg_color='#753A50',
            hover_color='#3D1021',
            text_color='white',
        )

        check_button.grid(
            row=0,
            column=0,
            padx=(0, 16),
        )
        
        self.match_status = self.label(
            check_frame,
            'Select both inputs to begin.',
            wraplength=300,
            anchor='center',
            justify='center',
        )

        self.match_status.grid(
            row=1,
            column=0,
            padx=16,
            pady=(0, 14),
            sticky='ew',
        )

        editor = ctk.CTkFrame(self.main_card, fg_color='transparent')
        editor.grid(row=4, column=0, padx=(26, 12), sticky='nsew')
        editor.grid_columnconfigure(0, weight=1)
        self.label(editor, '02   Message', 20, True).grid(row=0, column=0, sticky='w', pady=(0, 12))
        self.subject_entry = self.entry(editor, 'Email subject')
        self.subject_entry.grid(row=1, column=0, sticky='ew')
        self.label(editor, 'Message · use [Name] to personalise').grid(row=2, column=0, sticky='w', pady=(12, 5))
        self.body_box = self.textbox(editor, 190)
        self.body_box.grid(row=3, column=0, sticky='ew')
        self.put_text(self.body_box, 'Dear [Name],\n\nPlease find your certificate attached.')
        self.label(editor, 'Signature').grid(row=4, column=0, sticky='w', pady=(12, 5))
        self.signature_box = self.textbox(editor, 75)
        self.signature_box.grid(row=5, column=0, sticky='ew')
        self.put_text(self.signature_box, 'Best regards,\nEvents Team')
        template_actions = ctk.CTkFrame(editor, fg_color='transparent')
        template_actions.grid(row=6, column=0, sticky='ew', pady=12)
        template_actions.grid_columnconfigure((0, 1), weight=1)
        self.button(template_actions, 'Load template', self.load).grid(row=0, column=0, padx=(0, 4), sticky='ew')
        self.button(template_actions, 'Save template', self.save).grid(row=0, column=1, padx=(4, 0), sticky='ew')

        preview = ctk.CTkFrame(self.main_card, fg_color='transparent')
        preview.grid(row=4, column=1, padx=(12, 26), sticky='nsew')
        preview.grid_columnconfigure(0, weight=1)
        self.label(preview, '03   Preview', 20, True).grid(row=0, column=0, sticky='w', pady=(0, 12))
        self.preview_box = self.textbox(preview, 348, editable=False)
        self.preview_box.grid(row=1, column=0, sticky='ew')
        self.put_text(self.preview_box, 'Your personalised message will appear here.\n\nCheck matches, then select Preview.', True)
        nav = ctk.CTkFrame(preview, fg_color='transparent')
        nav.grid(row=2, column=0, sticky='ew', pady=(12, 4))
        nav.grid_columnconfigure(1, weight=1)
        self.button(nav, '‹', lambda: self.preview(-1), width=40).grid(row=0, column=0)
        self.preview_count = self.label(nav, 'No preview')
        self.preview_count.grid(row=0, column=1)
        self.button(nav, '›', lambda: self.preview(1), width=40).grid(row=0, column=2)
        self.button(preview, 'Preview messages', self.preview).grid(row=3, column=0, sticky='ew', pady=(4, 12))

        footer = ctk.CTkFrame(self.workspace, fg_color=CARD, corner_radius=16,
                              border_width=1, border_color=BORDER)
        footer.grid(row=2, column=0, sticky='ew', padx=32, pady=(4, 16))
        footer.grid_columnconfigure(0, weight=1)
        self.status = self.label(footer, 'Ready when you are.', wraplength=700)
        self.status.grid(row=0, column=0, padx=20, sticky='w', pady=(10, 4))
        self.progress = ctk.CTkProgressBar(footer, progress_color=ACCENT, fg_color=BORDER)
        self.progress.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 10))
        self.progress.set(0)
        actions = ctk.CTkFrame(footer, fg_color='transparent')
        actions.grid(row=2, column=0, sticky='ew', padx=20, pady=(0, 12))
        actions.grid_columnconfigure(2, weight=1)
        self.button(actions, 'Test email', self.test_email, width=100).grid(row=0, column=0, padx=(0, 8))
        self.button(actions, 'Dry run', lambda: self.start_batch(True), width=100).grid(row=0, column=1)
        self.stop_button = self.button(actions, 'Stop', self.stop, register=False, width=70)
        self.stop_button.grid(row=0, column=2, sticky='w', padx=8)
        self.stop_button.configure(state='disabled')
        self.button(actions, 'Review & send', lambda: self.start_batch(False), primary=True).grid(row=0, column=3)
        self.button(self.main_card, 'Activity & file details', self.toggle_log, register=False).grid(
            row=8, column=0, columnspan=2, sticky='w', padx=26, pady=(0, 18))
        self.log_box = self.textbox(self.main_card, 170, editable=False)
        for textbox in (
            self.body_box,
            self.signature_box,
            self.preview_box,
            self.log_box,
        ):
            textbox._textbox.bind(
                "<MouseWheel>",
                lambda event, box=textbox: self.handle_textbox_scroll(
                    event, box
                ),
            )

            textbox._canvas.bind(
                "<MouseWheel>",
                self.scroll_workspace,
            )

    def template(self):
        return {'subject': self.subject_entry.get().strip(),
                'body': self.body_box.get('1.0', 'end-1c'),
                'signature': self.signature_box.get('1.0', 'end-1c')}

    def toggle_log(self):
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_box.grid(row=9, column=0, columnspan=2, sticky='ew', padx=26, pady=(0, 20))
        else:
            self.log_box.grid_remove()

    def log(self, text):
        self.log_box.configure(state='normal')
        self.log_box.insert('end', text + '\n')
        self.log_box.see('end')
        self.log_box.configure(state='disabled')

    def error(self, title, error):
        self.status.configure(text=str(error))
        self.log(f'{title}: {error}')
        messagebox.showerror(title, str(error), parent=self)

    def set_busy(self, value, operation=None):
        self.busy, self.operation = value, operation if value else None
        for control in self.controls:
            control.configure(state='disabled' if value else 'normal')
        for control in (self.connect_button, self.switch_button, self.continue_button):
            control.configure(state='disabled' if value else 'normal')
        self.stop_button.configure(state='normal' if value and operation == 'batch' else 'disabled')
        self.hide_account_menu()

    def connect(self, interactive=True, choose_account=False):
        if self.busy:
            return
        self.set_busy(True, 'auth')
        self.auth_status.configure(text='Complete sign-in in your browser…' if interactive else 'Checking your saved session…')
        def worker():
            try:
                self.events.put(('account', connect_account(interactive, choose_account)))
            except Exception as error:
                self.events.put(('auth_error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def apply_account(self, account):
        self.close_history()
        if self.account and account and self.account.subject != account.subject:
            self.campaign_entry.delete(0, 'end')
            self.invalidate_matches()
        self.account = account
        self.profile_image = None
        if account is None:
            self.account_name.configure(text='Connect your account')
            self.account_email.configure(text='Sign in securely in your browser.')
            for widget in (self.account_avatar, self.avatar_button):
                widget.set_profile()
            self.continue_button.pack_forget()
            self.switch_button.pack_forget()
            self.connect_button.pack(padx=40, pady=5, before=self.auth_status)
            return
        if account.picture:
            try:
                from PIL import Image, ImageDraw, ImageOps
                photo = ImageOps.fit(Image.open(BytesIO(account.picture)).convert('RGBA'), (80, 80))
                mask = Image.new('L', (80, 80), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 79, 79), fill=255)
                photo.putalpha(mask)
                self.profile_image = photo
            except Exception as error:
                print(f"Could not load profile image: {error}")
        initial = account.name.strip()[:1].upper() or 'G'

        for widget in (self.account_avatar, self.avatar_button):
            widget.set_profile(self.profile_image, initial)
        self.account_name.configure(text=account.name)
        self.account_email.configure(text=account.email)
        self.sender_label.configure(text=account.email)
        self.connect_button.pack_forget()
        self.continue_button.pack(padx=40, pady=5, before=self.auth_status)
        self.switch_button.pack(padx=40, pady=5, before=self.auth_status)

    def show_workspace(self):
        if self.account and not self.busy:
            self.workspace.tkraise()

    def toggle_account_menu(self):
        if self.account_menu:
            self.hide_account_menu()
            return
        if not self.account:
            return
        menu = ctk.CTkFrame(self.workspace, fg_color=CARD, corner_radius=14,
                           border_color=BORDER, border_width=1)
        self.account_menu = menu
        menu.place(relx=1, x=-32, y=64, anchor='ne')
        menu.lift()
        self.label(menu, self.account.name, 16, True).pack(padx=22, pady=(18, 3))
        self.label(menu, self.account.email).pack(padx=22, pady=(0, 14))
        self.button(menu, 'History', self.show_history, register=False, width=220).pack(padx=14, pady=4)
        logout = self.button(menu, 'Log out', self.logout, register=False, width=220)
        logout.pack(padx=14, pady=4)
        logout.configure(
            fg_color="#FFE600",       
            hover_color="#C0B955",    
            text_color="#080000",    
        )
        quit = self.button(menu, 'Quit', self.close_app, register=False, width=220)
        quit.pack(padx=14, pady=4)
        quit.configure(
            fg_color="#FF0000",       
            hover_color="#990000",    
            text_color="black",    
        )

  
        

    def close_history(self):
        if self.history_window is not None:
            if self.history_window.winfo_exists():
                self.history_window.destroy()
            self.history_window = None

    def show_history(self):
        if self.account is None:
            return
        self.hide_account_menu()
        if self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.deiconify()
            self.history_window.lift()
            self.history_window.refresh()
            return
        self.history_window = HistoryWindow(self, self.account)
        self.history_window.protocol('WM_DELETE_WINDOW', self.close_history)

    def hide_account_menu(self):
        if self.account_menu:
            self.account_menu.destroy()
            self.account_menu = None

    def dismiss_menu(self, event):
        if not self.account_menu:
            return
        widget = event.widget
        while widget is not None:
            if widget in (self.account_menu, self.avatar_button):
                return
            widget = getattr(widget, 'master', None)
        self.hide_account_menu()

    def logout(self):
        if self.busy:
            return
        try:
            logout_account()
        except OSError as error:
            self.error('Could not log out', error)
            return
        self.hide_account_menu()
        self.apply_account(None)
        self.sender_label.configure(text='')
        self.campaign_entry.delete(0, 'end')
        self.invalidate_matches()
        self.excel_path = self.certificate_folder = ''
        self.excel_label.configure(text='No spreadsheet selected')
        self.cert_label.configure(text='No folder selected')
        self.put_text(self.log_box, '', True)
        self.progress.set(0)
        self.auth_status.configure(text='Logged out of this application.')
        self.account_page.tkraise()

    def invalidate_matches(self):
        self.participants, self.preview_people = [], []
        self.matched = False
        self.preview_index = 0
        self.match_status.configure(text='Check matches to continue.')
        self.preview_count.configure(text='No preview')
        self.put_text(self.preview_box, 'Check matches, then preview your message.', True)

    def choose_excel(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self, title='Choose participant spreadsheet',
                                          filetypes=[('Excel', '*.xlsx *.xlsm')])
        if path:
            self.excel_path = path
            self.excel_label.configure(text=Path(path).name + ' ✅')
            self.invalidate_matches()
            self.log(f'Excel: {path}')

    def choose_certificates(self):
        if self.busy:
            return
        path = filedialog.askdirectory(parent=self, title='Choose certificates')
        if path:
            self.certificate_folder = path
            self.cert_label.configure(text=Path(path).name + ' ✅')
            self.invalidate_matches()
            self.log(f'Certificates: {path}')

    def match(self):
        if self.busy:
            return
        self.invalidate_matches()
        if not self.excel_path or not self.certificate_folder:
            self.error('Select your files', 'Choose an Excel file and a certificate folder first.')
            return
        try:
            people = read_participants(self.excel_path)
            certificates = get_certificates(self.certificate_folder)
            ready = 0
            for person in people:
                key = normalize_name(person['name'])
                candidates = [cert for cert in certificates if key and cert['normalized_name'] == key]
                person['certificate'] = candidates[0]['path'] if len(candidates) == 1 else None
                if person['certificate']:
                    ready += 1
                    self.log(f"Matched: {person['name']} → {person['certificate']}")
                else:
                    reason = 'multiple matching PDFs' if len(candidates) > 1 else 'no matching PDF'
                    self.log(f"Needs review: {person['name']} — {reason}")
            self.participants, self.matched = people, True
            self.match_status.configure(text=f'{ready} matched · {len(people) - ready} need review')
            self.status.configure(text='Matches checked. Review your personalised messages.')
        except Exception as error:
            self.error('Matching failed', error)

    def preview(self, offset=0):
        if self.busy:
            return
        self.preview_people = [p for p in self.participants if p.get('certificate')]
        if not self.matched or not self.preview_people:
            self.error('No preview available', 'Check matches and resolve missing certificates first.')
            return
        self.preview_index = (self.preview_index + offset) % len(self.preview_people)
        person = self.preview_people[self.preview_index]
        try:
            mail = personalise_template(self.template(), person)
            self.put_text(self.preview_box,
                          f"To: {person['email']}\nSubject: {mail['subject']}\n\n"
                          f"{mail['body']}\n\nAttachment: {Path(person['certificate']).name}", True)
            self.preview_count.configure(text=f'{self.preview_index + 1} of {len(self.preview_people)}')
            self.status.configure(text='Preview updated. Nothing has been sent.')
        except Exception as error:
            self.error('Preview failed', error)

    def save(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.json',
                                           filetypes=[('Email template', '*.json')])
        if path:
            try:
                save_template(path, self.template())
                self.status.configure(text='Template saved.')
            except Exception as error:
                self.error('Save failed', error)

    def load(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[('Email template', '*.json')])
        if path:
            try:
                template = load_template(path)
                self.subject_entry.delete(0, 'end')
                self.subject_entry.insert(0, template['subject'])
                self.put_text(self.body_box, template['body'])
                self.put_text(self.signature_box, template['signature'])
                self.put_text(self.preview_box, 'Template loaded. Refresh the preview to review changes.', True)
                self.status.configure(text='Template loaded.')
            except Exception as error:
                self.error('Load failed', error)

    def jobs(self):
        if not self.matched:
            raise ValueError('Check matches before continuing.')
        return prepare_email_jobs(self.participants, self.template())

    def test_email(self):
        if self.busy or not self.account:
            return
        try:
            job = self.jobs()[0]
        except Exception as error:
            self.error('Cannot prepare test', error)
            return
        if not messagebox.askyesno('Send one test email',
                f"Send to your connected account: {self.account.email}?\n\n"
                f"Personalised for: {job['name']}\nAttachment: {job['certificate_path']}", parent=self):
            return
        account = self.account
        self.set_busy(True, 'test')
        self.status.configure(text='Sending a test to your connected account…')
        def worker():
            try:
                message_id = send_certificate_email(account.gmail_client(), account.email,
                    '[TEST] ' + job['subject'], job['body'], job['certificate_path'])
                self.events.put(('test_success', message_id))
            except Exception as error:
                self.events.put(('test_error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def start_batch(self, dry_run=True):
        if self.busy or not self.account:
            return
        campaign = self.campaign_entry.get().strip()
        try:
            jobs = self.jobs()
            if not dry_run and not campaign:
                raise ValueError('Enter a campaign name. Reuse it when resuming this mailing.')
            if not dry_run and len(jobs) > 3:
                raise ValueError('The existing initial live-test limit is three recipients.')
        except Exception as error:
            self.error('Cannot start', error)
            return
        if not dry_run:
            review = ctk.CTkToplevel(self)
            review.title('Review real emails')
            review.geometry('700x570')
            review.transient(self)
            review.grab_set()
            self.label(review, f'Sending from {self.account.email}', 16, True).pack(padx=20, pady=15)
            body = self.textbox(review, 345, editable=False)
            body.pack(fill='both', expand=True, padx=20)
            self.put_text(body, '\n\n' + ('\n\n' + '─' * 45 + '\n\n').join(
                f"To: {job['recipient']}\nSubject: {job['subject']}\n"
                f"Attachment: {job['certificate_path']}\n\n{job['body']}" for job in jobs), True)
            self.label(review, f'Type the campaign name to confirm: {campaign}').pack(pady=10)
            confirmation = ctk.CTkEntry(review, width=400)
            confirmation.pack()
            def confirm():
                if confirmation.get().strip() != campaign:
                    messagebox.showwarning('Campaign name does not match', 'Type the exact campaign name.', parent=review)
                    return
                review.destroy()
                self.launch_batch(jobs, campaign, False)
            self.button(review, f'Send {len(jobs)} real emails', confirm,
                         primary=True, register=False).pack(pady=12)
            return
        self.launch_batch(jobs, campaign, True)

    def launch_batch(self, jobs, campaign, dry_run):
        if self.busy:
            return
        account = self.account
        self.dry_run = dry_run
        self.stop_event.clear()
        self.set_busy(True, 'batch')
        self.progress.set(0)
        self.status.configure(text='Starting dry run…' if dry_run else 'Starting campaign…')
        self.log('DRY RUN — no emails will be sent.' if dry_run else f'Campaign: {campaign} · {account.email}')
        def worker():
            try:
                send_batches(None if dry_run else account.gmail_client(), jobs,
                             self.events, self.stop_event, batch_size=10,
                             message_delay=2, batch_pause=30, dry_run=dry_run,
                             campaign_id=campaign, sender_id=account.subject)
            except Exception as error:
                self.events.put(('batch_error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def stop(self):
        if self.operation == 'batch':
            self.stop_event.set()
            self.stop_button.configure(state='disabled')
            self.status.configure(text='Stopping after the current request…')

    def poll_events(self):
        for _ in range(100):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if isinstance(event, tuple):
                kind, value = event
                self.set_busy(False)
                if kind == 'account':
                    self.apply_account(value)
                    self.auth_status.configure(text='Account ready. Continue when you are.' if value else 'Connect to begin.')
                elif kind == 'auth_error':
                    self.auth_status.configure(text='Could not connect. Try again with Google.')
                    self.log(f'Connection: {value}')
                    messagebox.showerror('Connection failed', value, parent=self)
                elif kind == 'test_success':
                    self.status.configure(text='Test email accepted by Gmail.')
                    self.log(f'Test accepted · message ID {value}')
                else:
                    self.error('Sending was not confirmed', value + '\nCheck Sent before retrying an uncertain request.')
                continue
            kind = event['type']
            if kind == 'started':
                self.batch_total = event['total']
            elif kind == 'sending':
                self.status.configure(text=f"{'Simulating' if self.dry_run else 'Processing'} {event['index']} of {event['total']}")
            elif kind in ('simulated', 'sent', 'skipped'):
                self.log(f"[{kind.upper()}] {event['recipient']}" +
                         (f" · {event['message_id']}" if event.get('message_id') else ''))
                self.progress.set(event['index'] / max(1, self.batch_total))
            elif kind == 'waiting':
                self.status.configure(text=f"Waiting {event['seconds']} seconds…")
            elif kind in ('failed', 'unconfirmed'):
                self.log(f"{event['recipient']}: {event['error']}")
                if not self.log_visible:
                    self.toggle_log()
            elif kind == 'finished':
                self.set_busy(False)
                summary = f"{'Dry run' if event['dry_run'] else 'Campaign'} {event['reason'].replace('_', ' ')} · {event['processed']} of {event['total']} processed"
                self.status.configure(text=summary)
                self.log(summary)
        self.after(100, self.poll_events)

    def close_app(self):
        if self.busy:
            self.stop()
            messagebox.showinfo('Operation in progress',
                'Wait for the current operation to finish, then quit. A running batch has been asked to stop.', parent=self)
            return
        self.destroy()

    def destroy(self):
        # Cancel Tk timers before tearing down widgets (also important in tests).
        for timer in self.tk.call('after', 'info'):
            self.tk.call('after', 'cancel', timer)
        super().destroy()


def main():
    ctk.set_appearance_mode('light')
    MailerApp().mainloop()


if __name__ == '__main__':
    main()
