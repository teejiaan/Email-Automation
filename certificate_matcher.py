import os
import re


def normalize_name(value):
    """
    Converts names into a standard format for comparison.

    Example:
        "John Tan"     -> "johntan"
        "JOHN_TAN"     -> "johntan"
        "John-Tan"     -> "johntan"
    """

    value = value.lower()

    # Remove everything except letters and numbers
    value = re.sub(r"[^a-z0-9]", "", value)

    return value


def get_certificates(folder_path):
    certificates = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            full_path = os.path.join(folder_path, filename)

            # Remove ".pdf"
            filename_without_extension = os.path.splitext(filename)[0]

            certificates.append(
                {
                    "filename": filename,
                    "path": full_path,
                    "normalized_name": normalize_name(
                        filename_without_extension
                    ),
                }
            )

    return certificates


def find_certificate(participant_name, certificates):
    normalized_participant_name = normalize_name(participant_name)

    for certificate in certificates:
        if certificate["normalized_name"] == normalized_participant_name:
            return certificate

    return None