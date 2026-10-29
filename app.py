import customtkinter as ctk
import tkinter as tk
import queue
import threading

from gmail_service import connect_gmail, send_certificate_email
from batch_sender import prepare_email_jobs, send_batches
from tkinter import filedialog, messagebox, simpledialog
from main import choose_excel_file, choose_certificate_folder
from excel_reader import read_participants
from certificate_matcher import get_certificates, find_certificate
from email_templates import (
    personalise_template,
    save_template,
    load_template,
)

# Function to handle the Excel file selection
def button_callback_excel():
    selected_path = choose_excel_file()

    if selected_path:
        excel_path.set(selected_path)

        excel_path_label.configure(
            text=f"[EXCEL SHEET SELECTED] : {selected_path}"
        )

        clear_matching_results()

# Function to handle the certificate folder selection
def button_callback_certificate():
    selected_folder = choose_certificate_folder()

    if selected_folder:
        certificate_folder_path.set(selected_folder)

        certificate_path_label.configure(
            text=f"[CERTIFICATE FOLDER SELECTED] : {selected_folder}"
        )

        clear_matching_results()

# Function to display the matching results in the results box
def display_results(text):
    results_box.configure(state="normal")
    results_box.delete("1.0", "end")
    results_box.insert("end", text)
    results_box.configure(state="disabled")

# Function to clear the matching results when a new file or folder is selected
def clear_matching_results():
    app_state["participants"] = []
    app_state["matching_complete"] = False
    

    display_results("")
    status_label.configure(
        text="Selections changed. Match certificates again."
    )

# Function to match certificates with participants
def match_certificates():
    # Discard any previous matching result.
    app_state["participants"] = []
    app_state["matching_complete"] = False

    excel_file = excel_path.get()
    certificate_folder = certificate_folder_path.get()

    if not excel_file:
        display_results("Please select an Excel file.")
        status_label.configure(text="Excel file required.")
        return

    if not certificate_folder:
        display_results("Please select a certificate folder.")
        status_label.configure(text="Certificate folder required.")
        return

    try:
        participants = read_participants(excel_file)
        certificates = get_certificates(certificate_folder)

        results = []
        ready_count = 0
        missing_count = 0

        for participant in participants:
            certificate = find_certificate(
                participant["name"],
                certificates,
            )

            if certificate:
                participant["certificate"] = certificate["path"]

                results.append(
                    f"[READY] {participant['name']} | "
                    f"{participant['email']} | "
                    f"{certificate['filename']}"
                )
                ready_count += 1

            else:
                participant["certificate"] = None

                results.append(
                    f"[MISSING] {participant['name']} | "
                    f"{participant['email']} | "
                    "No certificate found"
                )
                missing_count += 1

        summary = (
            f"Participants found: {len(participants)}\n"
            f"Certificates found: {len(certificates)}\n"
            f"Ready: {ready_count}\n"
            f"Missing: {missing_count}"
        )

        details = "\n".join(results) or "No participants found."
        display_results(details + "\n\n" + summary)

        status_label.configure(
            text=f"Matching complete | "
                 f"Ready: {ready_count} | Missing: {missing_count}"
        )

        # Retain the data for other callbacks.
        app_state["participants"] = participants
        app_state["matching_complete"] = True

    except Exception as error:
        display_results(f"An error occurred: {error}")
        status_label.configure(text="Matching failed.")

# Function to get the email template from the GUI
def get_template_from_gui():
    return {
        "subject": subject_entry.get().strip(),
        "body": body_textbox.get("1.0", "end-1c"),
        "signature": signature_textbox.get("1.0", "end-1c"),
    }

# Function to preview the emails for matched participants
def preview_emails():
    if not app_state["matching_complete"]:
        messagebox.showwarning(
            "Match required",
            "Please match certificates first.",
            parent=app,
        )
        return

    matched_participants = [
        participant
        for participant in app_state["participants"]
        if participant.get("certificate")
    ]

    if not matched_participants:
        messagebox.showwarning(
            "No matches",
            "No participants have matching certificates.",
            parent=app,
        )
        return

    try:
        template = get_template_from_gui()
        previews = []

        for index, participant in enumerate(matched_participants, start=1):
            message = personalise_template(template, participant)

            previews.append(
                f"EMAIL {index} OF {len(matched_participants)}\n"
                f"To: {participant['email']}\n"
                f"Subject: {message['subject']}\n"
                f"Attachment: {participant['certificate']}\n\n"
                f"{message['body']}"
            )

        separator = "\n\n" + "=" * 60 + "\n\n"
        display_results(separator.join(previews))

        status_label.configure(
            text=f"Previewing {len(previews)} emails. Nothing has been sent."
        )

    except Exception as error:
        messagebox.showerror(
            "Preview failed",
            str(error),
            parent=app,
        )

# Function to save the email template to a file
def save_template_clicked():
    file_path = filedialog.asksaveasfilename(
        parent=app,
        title="Save Email Template",
        defaultextension=".json",
        filetypes=[("JSON templates", "*.json")],
    )

    if not file_path:
        return

    try:
        save_template(file_path, get_template_from_gui())
        status_label.configure(text="Email template saved.")

    except Exception as error:
        messagebox.showerror(
            "Save failed",
            str(error),
            parent=app,
        )

# Function to load an email template from a file and populate the GUI fields
def load_template_clicked():
    file_path = filedialog.askopenfilename(
        parent=app,
        title="Load Email Template",
        filetypes=[("JSON templates", "*.json")],
    )

    if not file_path:
        return

    try:
        template = load_template(file_path)

        subject_entry.delete(0, "end")
        subject_entry.insert(0, template["subject"])

        body_textbox.delete("1.0", "end")
        body_textbox.insert("1.0", template["body"])

        signature_textbox.delete("1.0", "end")
        signature_textbox.insert("1.0", template["signature"])

        status_label.configure(
            text="Template loaded. Click Preview Emails to refresh the preview."
        )

    except Exception as error:
        messagebox.showerror(
            "Load failed",
            str(error),
            parent=app,
        )

# Function to save the email template to a file
def save_template_callback():
    file_path = filedialog.asksaveasfilename(
        parent=app,
        title="Save email template",
        defaultextension=".json",
        filetypes=[("JSON templates", "*.json")],
    )

    if not file_path:
        return

    try:
        save_template(file_path, get_template_from_gui())
        status_label.configure(text="Template saved.")
    except Exception as error:
        messagebox.showerror("Save failed", str(error), parent=app)

# Function to load an email template from a file and populate the GUI fields
def load_template_callback():
    file_path = filedialog.askopenfilename(
        parent=app,
        title="Load email template",
        filetypes=[("JSON templates", "*.json")],
    )

    if not file_path:
        return

    try:
        template = load_template(file_path)

        subject_entry.delete(0, "end")
        subject_entry.insert(0, template["subject"])

        body_textbox.delete("1.0", "end")
        body_textbox.insert("1.0", template["body"])

        signature_textbox.delete("1.0", "end")
        signature_textbox.insert("1.0", template["signature"])

        display_results("")
        status_label.configure(
            text="Template loaded. Click Preview Emails to review it."
        )

    except Exception as error:
        messagebox.showerror("Load failed", str(error), parent=app)

# Function to initiate the Gmail connection process in a separate thread
def connect_gmail_callback():
    gmail_connect_button.configure(state="disabled")
    gmail_status_label.configure(
        text="Connecting — complete Google sign-in in your browser."
    )

    worker = threading.Thread(
        target=connect_gmail_worker,
        daemon=True,
    )
    worker.start()

    app.after(100, check_gmail_connection)

# Function to handle the Gmail connection in a separate thread
def connect_gmail_worker():
    try:
        service = connect_gmail()
        gmail_connection_results.put(("success", service))
    except Exception as error:
        gmail_connection_results.put(("error", str(error)))

# Function to check the Gmail connection results and update the GUI accordingly
def check_gmail_connection():
    try:
        outcome, value = gmail_connection_results.get_nowait()
    except queue.Empty:
        app.after(100, check_gmail_connection)
        return

    if outcome == "success":
        app_state["gmail_service"] = value

        gmail_status_label.configure(
            text="Gmail authorised."
        )
        gmail_connect_button.configure(
            text="Gmail Connected",
            state="disabled",
        )

    else:
        app_state["gmail_service"] = None

        gmail_status_label.configure(
            text="Gmail connection failed."
        )
        gmail_connect_button.configure(state="normal")

        messagebox.showerror(
            "Gmail connection failed",
            value,
            parent=app,
        )

# Function to send a test email to the user with a matched certificate
def send_test_email_callback():
    if app_state["batch_running"] or app_state["test_running"]:
        return
    service = app_state.get("gmail_service")

    if service is None:
        messagebox.showwarning(
            "Gmail required",
            "Please connect Gmail first.",
            parent=app,
        )
        return

    if not app_state["matching_complete"]:
        messagebox.showwarning(
            "Match required",
            "Please match certificates first.",
            parent=app,
        )
        return

    participant = next(
        (
            person
            for person in app_state["participants"]
            if person.get("certificate")
        ),
        None,
    )

    if participant is None:
        messagebox.showwarning(
            "No certificate",
            "There are no matched certificates to test.",
            parent=app,
        )
        return

    try:
        message = personalise_template(
            get_template_from_gui(),
            participant,
        )
    except Exception as error:
        messagebox.showerror(
            "Invalid template",
            str(error),
            parent=app,
        )
        return

    recipient = simpledialog.askstring(
        "Test recipient",
        "Enter your own email address for this test:",
        parent=app,
    )

    if not recipient:
        return

    recipient = recipient.strip()

    # Basic single-address check, not mailbox verification.
    if (
        recipient.count("@") != 1
        or recipient.startswith("@")
        or recipient.endswith("@")
        or any(char.isspace() for char in recipient)
        or "," in recipient
        or ";" in recipient
    ):
        messagebox.showerror(
            "Invalid address",
            "Enter one email address.",
            parent=app,
        )
        return

    subject = "[TEST] " + message["subject"]
    certificate_path = participant["certificate"]

    confirmed = messagebox.askyesno(
        "Send test email",
        f"Send one real email?\n\n"
        f"To: {recipient}\n"
        f"Personalised for: {participant['name']}\n"
        f"Subject: {subject}\n"
        f"Attachment: {certificate_path}\n\n"
        f"{message['body']}",
        parent=app,
    )

    if not confirmed:
        return

    app_state["test_running"] = True
    start_batch_button.configure(state="disabled")
    send_batch_button.configure(state="disabled")
    send_test_button.configure(state="disabled")
    gmail_status_label.configure(text="Sending test email...")

    threading.Thread(
        target=send_test_email_worker,
        args=(
            service,
            recipient,
            subject,
            message["body"],
            certificate_path,
        ),
        daemon=True,
    ).start()

    app.after(100, check_test_email_result)

# Function to handle sending the test email in a separate thread
def send_test_email_worker(
    service,
    recipient,
    subject,
    body,
    certificate_path,
):
    try:
        message_id = send_certificate_email(
            service,
            recipient,
            subject,
            body,
            certificate_path,
        )
        gmail_send_results.put(("success", message_id))

    except Exception as error:
        gmail_send_results.put(("error", str(error)))

# Function to check the test email sending results and update the GUI accordingly
def check_test_email_result():
    try:
        outcome, value = gmail_send_results.get_nowait()
    except queue.Empty:
        app.after(100, check_test_email_result)
        return
    
    app_state["test_running"] = False
    start_batch_button.configure(state="normal")
    send_batch_button.configure(state="normal")
    send_test_button.configure(state="normal")

    if outcome == "success":
        gmail_status_label.configure(
            text="Test email accepted by Gmail."
        )
        messagebox.showinfo(
            "Test sent",
            f"Gmail accepted the email.\n\nMessage ID: {value}",
            parent=app,
        )

    else:
        gmail_status_label.configure(
            text="Sending was not confirmed."
        )
        messagebox.showerror(
            "Sending was not confirmed",
            f"{value}\n\n"
            "If this was a connection error or timeout, "
            "check Gmail's Sent folder before retrying.",
            parent=app,
        )


def set_batch_controls(running):
    app_state["batch_running"] = running
    state = "disabled" if running else "normal"

    # Freeze selections and template editing during a run.
    for widget in (
        excel_button,
        certificate_button,
        match_button,
        subject_entry,
        body_textbox,
        signature_textbox,
        save_button,
        load_button,
        preview_button,
        send_test_button,
        start_batch_button,
        campaign_entry,
        send_batch_button,
    ):
        widget.configure(state=state)

    stop_batch_button.configure(
        state="normal" if running else "disabled"
    )


def append_batch_output(text):
    results_box.configure(state="normal")
    results_box.insert("end", text + "\n")
    results_box.see("end")
    results_box.configure(state="disabled")


def start_batch_callback(dry_run=True):
    if app_state["batch_running"] or app_state["test_running"]:
        return

    if not app_state["matching_complete"]:
        messagebox.showwarning(
            "Match required",
            "Please match certificates first.",
            parent=app,
        )
        return

    campaign_id = campaign_entry.get().strip()
    service = app_state.get("gmail_service")

    if not dry_run:
        if service is None:
            messagebox.showwarning(
                "Gmail required",
                "Please connect Gmail first.",
                parent=app,
            )
            return

        if not campaign_id:
            messagebox.showwarning(
                "Campaign ID required",
                "Enter a campaign ID for this mailing.",
                parent=app,
            )
            return

    try:
        jobs = prepare_email_jobs(
            app_state["participants"],
            get_template_from_gui(),
        )
    except Exception as error:
        messagebox.showerror(
            "Cannot prepare batch",
            str(error),
            parent=app,
        )
        return

    # Temporary limit for the first live integration test.
    if not dry_run and len(jobs) > 3:
        messagebox.showwarning(
            "Initial live test",
            "For now, use an Excel file with at most three "
            "reviewed test recipients.",
            parent=app,
        )
        return

    mode = "Dry run" if dry_run else "Real sending"

    if dry_run:
        details = (
            f"Simulate {len(jobs)} emails?\n\n"
            "No emails will be sent."
        )
    else:
        recipients = "\n".join(
            f"{job['name']} — {job['recipient']}"
            for job in jobs
        )
        details = (
            f"Send real emails for campaign '{campaign_id}'?\n\n"
            f"{recipients}\n\n"
            "Previously confirmed sends will be skipped.\n"
            "Confirm that you reviewed the messages and PDF paths."
        )

    confirmed = messagebox.askyesno(
        mode,
        details
        + "\n\nBatch size: 10"
        + "\nBetween messages: 2 seconds"
        + "\nBetween batches: 30 seconds",
        parent=app,
    )

    if not confirmed:
        return

    while True:
        try:
            batch_progress_queue.get_nowait()
        except queue.Empty:
            break

    batch_stop_event.clear()
    app_state["batch_dry_run"] = dry_run

    set_batch_controls(True)
    batch_progress_bar.set(0)

    display_results(f"{mode.upper()}\n")
    batch_status_label.configure(text=f"Starting {mode.lower()}...")

    threading.Thread(
        target=batch_worker,
        args=(jobs, service, campaign_id, dry_run),
        daemon=True,
    ).start()

    app.after(100, check_batch_progress)
    if app_state["batch_running"] or app_state["test_running"]:
        return

    if not app_state["matching_complete"]:
        messagebox.showwarning(
            "Match required",
            "Please match certificates first.",
            parent=app,
        )
        return

    try:
        jobs = prepare_email_jobs(
            app_state["participants"],
            get_template_from_gui(),
        )
    except Exception as error:
        messagebox.showerror(
            "Cannot prepare batch",
            str(error),
            parent=app,
        )
        return

    confirmed = messagebox.askyesno(
        "Start dry run",
        f"Simulate processing {len(jobs)} emails?\n\n"
        "Batch size: 10\n"
        "Between messages: 2 seconds\n"
        "Between batches: 30 seconds\n\n"
        "No emails will be sent.",
        parent=app,
    )

    if not confirmed:
        return

    # Clear any events left over from a previous run.
    while True:
        try:
            batch_progress_queue.get_nowait()
        except queue.Empty:
            break

    batch_stop_event.clear()
    set_batch_controls(True)
    batch_progress_bar.set(0)

    display_results("DRY RUN — no emails will be sent.\n")
    batch_status_label.configure(text="Starting dry run...")

    threading.Thread(
        target=batch_worker,
        args=(jobs,),
        daemon=True,
    ).start()

    app.after(100, check_batch_progress)


def batch_worker(jobs, service, campaign_id, dry_run):
    try:
        send_batches(
            service=service,
            jobs=jobs,
            progress_queue=batch_progress_queue,
            stop_event=batch_stop_event,
            batch_size=10,
            message_delay=2,
            batch_pause=30,
            dry_run=dry_run,
            campaign_id=campaign_id,
        )
    except Exception as error:
        batch_progress_queue.put({
            "type": "worker_error",
            "error": str(error),
        })


def stop_batch_callback():
    if app_state["batch_running"]:
        batch_stop_event.set()
        stop_batch_button.configure(state="disabled")
        batch_status_label.configure(text="Stopping...")


def check_batch_progress():
    # Process a bounded number of events to keep the GUI responsive.
    for _ in range(100):
        try:
            event = batch_progress_queue.get_nowait()
        except queue.Empty:
            break

        event_type = event["type"]

        if event_type == "started":
            app_state["batch_total"] = event["total"]

        elif event_type == "sending":
            action = (
                "Simulating"
                if app_state["batch_dry_run"]
                else "Processing"
            )
            batch_status_label.configure(
                text=f"{action} {event['index']} of {event['total']}"
            )

        elif event_type in ("simulated", "sent", "skipped"):
            append_batch_output(
                f"[{event_type.upper()}] {event['recipient']}"
            )

            total = app_state.get("batch_total", 0)
            if total:
                batch_progress_bar.set(event["index"] / total)

        elif event_type == "waiting":
            batch_status_label.configure(
                text=f"Waiting {event['seconds']} seconds..."
            )

        elif event_type in ("failed", "unconfirmed"):
            append_batch_output(
                f"[{event_type.upper()}] "
                f"{event['recipient']}: {event['error']}"
            )

        elif event_type == "worker_error":
            append_batch_output(f"[ERROR] {event['error']}")
            batch_status_label.configure(text="Processing failed.")
            set_batch_controls(False)
            return

        elif event_type == "finished":
            mode = "Dry run" if event["dry_run"] else "Campaign"

            summary = (
                f"{mode} {event['reason']}: "
                f"{event['processed']} of {event['total']} processed."
            )
            append_batch_output(summary)
            batch_status_label.configure(text=summary)
            set_batch_controls(False)
            return

    if app_state["batch_running"]:
        app.after(100, check_batch_progress)


def on_close():
    if app_state["batch_running"]:
        stop_batch_callback()
        messagebox.showinfo(
            "Stopping",
            "Stop has been requested. Wait for processing to finish, "
            "then close the window again.",
            parent=app,
        )
        return

    if app_state["test_running"]:
        messagebox.showinfo(
            "Sending in progress",
            "Wait for the test email result before closing.",
            parent=app,
        )
        return

    app.destroy()




# This is the main Grid for the application
app = ctk.CTk()
app.title("Email Automation")
app.geometry("1200x800")
app.grid_columnconfigure(0, weight=1, uniform="main")
app.grid_columnconfigure(1, weight=1, uniform="main")
app.grid_rowconfigure(6, weight=1)

excel_path = tk.StringVar(master=app, value="")
certificate_folder_path = tk.StringVar(master=app, value="")

app_state = {
    "participants": [],
    "matching_complete": False,
    "gmail_service": None,
    "batch_running": False,
    "test_running": False,
}

gmail_connection_results = queue.Queue()
gmail_send_results = queue.Queue()
batch_progress_queue = queue.Queue()
batch_stop_event = threading.Event()

# Create a Header for the application
title_label = ctk.CTkLabel(
    app,
    text="Certificate Email Automation",
    font=ctk.CTkFont(size=24, weight="bold"),
)
title_label.grid(
    row=0,
    column=0,
    padx=20,
    pady=(30, 5),
)

description_label = ctk.CTkLabel(
    app,
    text="Select your participant list and certificate folder.",
)
description_label.grid(
    row=1,
    column=0,
    padx=20,
    pady=(0, 20),
)



# Create a frame to hold the buttons
selection_frame = ctk.CTkFrame(app)
selection_frame.grid(
    row=2,
    column=0,
    padx=20,
    pady=10,
    sticky="ew",
)

selection_frame.grid_columnconfigure(0, weight=1)
selection_frame.grid_columnconfigure(1, weight=1)

excel_button = ctk.CTkButton(
    selection_frame,
    text="Select Excel File",
    command=button_callback_excel,
)
excel_button.grid(
    row=0,
    column=0,
    padx=15,
    pady=20,
    sticky="ew",
)

certificate_button = ctk.CTkButton(
    selection_frame,
    text="Select Certificate Folder",
    command=button_callback_certificate,
)
certificate_button.grid(
    row=0,
    column=1,
    padx=15,
    pady=20,
    sticky="ew",
)




# Create labels to display the selected paths
excel_path_label = ctk.CTkLabel(
    app,
    text="[EXCEL SHEET SELECTED] : None",
    anchor="w",
)
excel_path_label.grid(
    row=3,
    column=0,
    padx=20,
    sticky="ew",
)

certificate_path_label = ctk.CTkLabel(
    app,
     text="[CERTIFICATE FOLDER SELECTED] : None",
    anchor="w",
)
certificate_path_label.grid(
    row=4,
    column=0,
    padx=20,
    sticky="ew",
)


match_button = ctk.CTkButton(
    app,
    text="Match Certificates",
    command=match_certificates,
)
match_button.grid(
    row=5,
    column=0,
    padx=20,
    pady=10,
)

# Email template section


#Results box to display the results of the matching process
results_box = ctk.CTkTextbox(app, wrap="word")
results_box.grid(
    row=6,
    column=0,
    padx=20,
    pady=10,
    sticky="nsew",
)
results_box.configure(state="disabled")

status_label = ctk.CTkLabel(
    app,
    text="Select an Excel file and a certificate folder.",
)
status_label.grid(
    row=7,
    column=0,
    padx=20,
    pady=10,
)

# Email template editor
template_frame = ctk.CTkFrame(app)
template_frame.grid(
    row=6,
    column=1,
    padx=(0, 20),
    pady=10,
    sticky="nsew",
)
template_frame.grid_columnconfigure(0, weight=1)
template_frame.grid_rowconfigure(3, weight=1)

subject_label = ctk.CTkLabel(
    template_frame,
    text="Subject",
)
subject_label.grid(
    row=0, column=0, padx=15, pady=(10, 0), sticky="w"
)

subject_entry = ctk.CTkEntry(
    template_frame,
    placeholder_text="Your workshop certificate",
)
subject_entry.grid(
    row=1, column=0, padx=15, pady=5, sticky="ew"
)

body_label = ctk.CTkLabel(
    template_frame,
    text="Message — use [Name] for the participant's name",
)
body_label.grid(
    row=2, column=0, padx=15, pady=(10, 0), sticky="w"
)

body_textbox = ctk.CTkTextbox(
    template_frame,
    height=150,
    wrap="word",
)
body_textbox.grid(
    row=3, column=0, padx=15, pady=5, sticky="nsew"
)
body_textbox.insert(
    "1.0",
    "Dear [Name],\n\nPlease find your certificate attached.",
)

signature_label = ctk.CTkLabel(
    template_frame,
    text="Signature",
)
signature_label.grid(
    row=4, column=0, padx=15, pady=(10, 0), sticky="w"
)

signature_textbox = ctk.CTkTextbox(
    template_frame,
    height=70,
    wrap="word",
)
signature_textbox.grid(
    row=5, column=0, padx=15, pady=5, sticky="ew"
)
signature_textbox.insert("1.0", "Best regards,\nEvents Team")

template_buttons = ctk.CTkFrame(
    template_frame,
    fg_color="transparent",
)
template_buttons.grid(
    row=6, column=0, padx=15, pady=10, sticky="ew"
)
template_buttons.grid_columnconfigure((0, 1), weight=1)

save_button = ctk.CTkButton(
    template_buttons,
    text="Save Template",
    command=save_template_callback,
)
save_button.grid(
    row=0, column=0, padx=(0, 5), sticky="ew"
)

load_button = ctk.CTkButton(
    template_buttons,
    text="Load Template",
    command=load_template_callback,
)
load_button.grid(
    row=0, column=1, padx=(5, 0), sticky="ew"
)

preview_button = ctk.CTkButton(
    template_frame,
    text="Preview Emails",
    command=preview_emails,
)
preview_button.grid(
    row=7, column=0, padx=15, pady=(0, 15), sticky="ew"
)

gmail_frame = ctk.CTkFrame(app)
gmail_frame.grid(
    row=8,
    column=0,
    columnspan=2,
    padx=20,
    pady=(0, 15),
    sticky="ew",
)
gmail_frame.grid_columnconfigure(1, weight=1)

gmail_connect_button = ctk.CTkButton(
    gmail_frame,
    text="Connect Gmail",
    command=connect_gmail_callback,
)
gmail_connect_button.grid(
    row=0,
    column=0,
    padx=15,
    pady=10,
)

gmail_status_label = ctk.CTkLabel(
    gmail_frame,
    text="Gmail not connected.",
    anchor="w",
)
gmail_status_label.grid(
    row=0,
    column=1,
    padx=15,
    pady=10,
    sticky="ew",
)

send_test_button = ctk.CTkButton(
    gmail_frame,
    text="Send Test Email",
    command=send_test_email_callback,
)
send_test_button.grid(
    row=0,
    column=2,
    padx=15,
    pady=10,
)

batch_frame = ctk.CTkFrame(app)
batch_frame.grid(
    row=9,
    column=0,
    columnspan=2,
    padx=20,
    pady=(0, 15),
    sticky="ew",
)
batch_frame.grid_columnconfigure(2, weight=1)

start_batch_button = ctk.CTkButton(
    batch_frame,
    text="Start Batch — Dry Run",
    command=start_batch_callback,
)
start_batch_button.grid(
    row=0, column=0, padx=10, pady=10,
)

stop_batch_button = ctk.CTkButton(
    batch_frame,
    text="Stop",
    command=stop_batch_callback,
    state="disabled",
)
stop_batch_button.grid(
    row=0, column=1, padx=10, pady=10,
)

batch_status_label = ctk.CTkLabel(
    batch_frame,
    text="Ready for a dry run.",
    anchor="w",
)
batch_status_label.grid(
    row=0, column=2, padx=10, pady=10, sticky="ew",
)

batch_progress_bar = ctk.CTkProgressBar(batch_frame)
batch_progress_bar.grid(
    row=1,
    column=0,
    columnspan=3,
    padx=10,
    pady=(0, 10),
    sticky="ew",
)
batch_progress_bar.set(0)

campaign_label = ctk.CTkLabel(
    batch_frame,
    text="Campaign ID:",
)
campaign_label.grid(
    row=2, column=0, padx=10, pady=10, sticky="w",
)

campaign_entry = ctk.CTkEntry(
    batch_frame,
    placeholder_text="e.g. workshop-october-2026",
)
campaign_entry.grid(
    row=2, column=1, columnspan=2,
    padx=10, pady=10, sticky="ew",
)

send_batch_button = ctk.CTkButton(
    batch_frame,
    text="Send Real Emails",
    command=lambda: start_batch_callback(dry_run=False),
)
send_batch_button.grid(
    row=3, column=0, columnspan=3,
    padx=10, pady=(0, 10),
)

app.protocol("WM_DELETE_WINDOW", on_close)


app.mainloop()