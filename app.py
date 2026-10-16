import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
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
}

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

app.mainloop()