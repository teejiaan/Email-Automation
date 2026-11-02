"""Read-only, account-scoped mailing history."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from send_log import LOG_PATH

FONT_FAMILY = 'Consolas'

STATUS_LABELS = {
    'sent': 'Accepted by Gmail',
    'sending': 'In progress / unfinished',
    'unconfirmed': 'Unconfirmed',
}


def read_history(sender_id, path=LOG_PATH):
    """Do not create a database or expose legacy/other-account records."""
    path = Path(path)
    if not sender_id or not path.exists():
        return []
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sends'"
        ).fetchone():
            return []
        rows = connection.execute(
            'SELECT campaign_id, recipient, status, updated_at, message_id, error '
            'FROM sends ORDER BY updated_at DESC, campaign_id, recipient'
        ).fetchall()
    records = []
    for row in rows:
        try:
            key = json.loads(row['campaign_id'])
        except (ValueError, TypeError):
            continue
        if (not isinstance(key, list) or len(key) != 3
                or key[:2] != ['google-account', sender_id]
                or not isinstance(key[2], str)):
            continue
        record = dict(row)
        record['campaign_id'] = key[2]
        records.append(record)
    return records


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent, account):
        super().__init__(parent)
        self.sender_id = account.subject
        self.title('Mailing history')
        self.geometry('1000x620')
        self.minsize(760, 480)
        self.transient(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(self, text='Mailing history', font=ctk.CTkFont(family=FONT_FAMILY, size=23, weight='bold')).grid(
            row=0, column=0, sticky='w', padx=24, pady=(20, 0))
        ctk.CTkLabel(self, text=account.email).grid(row=1, column=0, sticky='w', padx=24)
        filters = ctk.CTkFrame(self, fg_color='transparent')
        filters.grid(row=2, column=0, sticky='ew', padx=24, pady=12)
        filters.grid_columnconfigure(0, weight=1)
        self.search = ctk.CTkEntry(filters, placeholder_text='Search campaign or recipient')
        self.search.grid(row=0, column=0, sticky='ew', padx=(0, 12))
        self.search.bind('<KeyRelease>', lambda event: self.render())
        self.status = ctk.CTkOptionMenu(filters, values=['All statuses', *STATUS_LABELS.values()],
                                       command=lambda value: self.render(), width=200)
        self.status.grid(row=0, column=1, padx=(0, 12))
        ctk.CTkButton(filters, text='Refresh', width=90, command=self.refresh).grid(row=0, column=2)
        table = ctk.CTkFrame(self)
        table.grid(row=3, column=0, sticky='nsew', padx=24)
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        columns = ('campaign_id', 'recipient', 'updated_at', 'status')
        style = ttk.Style(self)
        style.configure('History.Treeview', font=(FONT_FAMILY, 11), rowheight=28)
        style.configure('History.Treeview.Heading', font=(FONT_FAMILY, 11, 'bold'))
        self.tree = ttk.Treeview(table, columns=columns, show='headings', selectmode='browse',
                                 style='History.Treeview')
        for column, heading, width in zip(columns,
                ('Campaign', 'Recipient', 'Last updated (local)', 'Status'), (200, 260, 160, 190)):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, minwidth=80)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind('<<TreeviewSelect>>', self.show_details)
        self.summary = ctk.CTkLabel(self, text='', anchor='w')
        self.summary.grid(row=4, column=0, sticky='ew', padx=24, pady=6)
        self.details = ctk.CTkTextbox(self, height=110, wrap='word')
        self.details.grid(row=5, column=0, sticky='ew', padx=24, pady=(0, 8))
        ctk.CTkLabel(self, text='Accepted by Gmail does not confirm delivery. Dry runs and older records without a sender are not shown.',
                     wraplength=710).grid(row=6, column=0, padx=24, pady=(0, 16))
        self.set_monospace(self)
        self.records = []
        self.refresh()

    def set_monospace(self, parent):
        for widget in parent.winfo_children():
            if isinstance(widget, (ctk.CTkLabel, ctk.CTkEntry, ctk.CTkButton,
                                   ctk.CTkOptionMenu, ctk.CTkTextbox)):
                widget.cget('font').configure(family=FONT_FAMILY)
                if isinstance(widget, ctk.CTkOptionMenu):
                    widget.configure(dropdown_font=ctk.CTkFont(family=FONT_FAMILY))
            if isinstance(widget, ctk.CTkFrame):
                self.set_monospace(widget)

    def set_details(self, text):
        self.details.configure(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', text)
        self.details.configure(state='disabled')

    def refresh(self):
        try:
            self.records = read_history(self.sender_id)
        except (OSError, sqlite3.Error) as error:
            self.records = []
            self.render()
            self.summary.configure(text='Could not load history. Try Refresh.')
            self.set_details(str(error))
            return
        self.render()

    def render(self):
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        query = self.search.get().strip().casefold()
        status = self.status.get()
        self.visible = []
        for record in self.records:
            label = STATUS_LABELS.get(record['status'], record['status'])
            if status != 'All statuses' and label != status:
                continue
            if query not in (record['campaign_id'] + ' ' + record['recipient']).casefold():
                continue
            try:
                timestamp = datetime.fromisoformat(record['updated_at']).astimezone().strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                timestamp = record['updated_at']
            self.tree.insert('', 'end', iid=str(len(self.visible)), values=(
                record['campaign_id'], record['recipient'], timestamp, label))
            self.visible.append(record)
        self.summary.configure(text=f'{len(self.visible)} of {len(self.records)} records' if self.records
                               else 'No recorded sends for this account yet.')
        self.set_details('Select a record to see its details. “In progress / unfinished” may also mean an interrupted attempt; check Gmail before retrying.')

    def show_details(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        record = self.visible[int(selected[0])]
        self.set_details(
            f"Campaign: {record['campaign_id']}\nRecipient: {record['recipient']}\n"
            f"Status: {STATUS_LABELS.get(record['status'], record['status'])}\n"
            f"Gmail message ID: {record['message_id'] or 'Not recorded'}\n"
            f"Error: {record['error'] or 'None recorded'}")
