import tkinter as tk
from tkinter import filedialog

from excel_reader import read_participants
from certificate_matcher import get_certificates, find_certificate


def choose_excel_file():
    file_path = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[
            ("Excel Files", "*.xlsx *.xlsm"),
            ("All Files", "*.*"),
        ],
    )

    return file_path


def choose_certificate_folder():
    folder_path = filedialog.askdirectory(
        title="Select Certificate Folder"
    )

    return folder_path


def main():
    root = tk.Tk()
    root.withdraw()

    print("CERTIFICATE EMAIL AUTOMATION")
    print("=" * 60)

    # Ask user to choose Excel file
    print("Select the Excel file containing participant information...")

    excel_file = choose_excel_file()

    if not excel_file:
        print("No Excel file selected.")
        return

    print(f"Excel selected: {excel_file}")
    print()

    # Ask user to choose certificate folder
    print("Select the folder containing the PDF certificates...")

    certificate_folder = choose_certificate_folder()

    if not certificate_folder:
        print("No certificate folder selected.")
        return

    print(f"Certificate folder selected: {certificate_folder}")
    print()

    try:
        participants = read_participants(excel_file)

        certificates = get_certificates(
            certificate_folder
        )

        print("=" * 60)
        print(f"Participants found: {len(participants)}")
        print(f"Certificates found: {len(certificates)}")
        print("=" * 60)
        print()

        ready_count = 0
        missing_count = 0

        for participant in participants:

            certificate = find_certificate(
                participant["name"],
                certificates,
            )

            if certificate:

                participant["certificate"] = certificate["path"]

                print(
                    f"[READY] "
                    f"{participant['name']} | "
                    f"{participant['email']} | "
                    f"{certificate['filename']}"
                )

                ready_count += 1

            else:

                participant["certificate"] = None

                print(
                    f"[MISSING] "
                    f"{participant['name']} | "
                    f"{participant['email']} | "
                    f"No certificate found"
                )

                missing_count += 1

        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Ready: {ready_count}")
        print(f"Missing certificates: {missing_count}")

    except Exception as error:
        print()
        print(f"ERROR: {error}")

    finally:
        root.destroy()


if __name__ == "__main__":
    main()