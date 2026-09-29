import customtkinter as ctk
import tkinter as tk

from main import choose_excel_file, choose_certificate_folder
from excel_reader import read_participants
from certificate_matcher import get_certificates, find_certificate

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




# This is the main Grid for the application
app = ctk.CTk()
app.title("Email Automation")
app.geometry("1200x800")
app.grid_columnconfigure(0, weight=1)
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



app.mainloop()