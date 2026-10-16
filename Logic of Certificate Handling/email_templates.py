import json
from pathlib import Path

template = {
    "subject": "Your certificate, [Name]",
    "body": "Dear [Name],\n\nPlease find your certificate attached.",
    "signature": "Best regards,\nEvents Team",
}

participant = {
    "name": "John Tan",
    "email": "john@example.com",
    "certificate": "C:/Certificates/John Tan.pdf",
}


def personalise_template(template, participant):
    validate_template(template)

    name = participant["name"].strip()

    if not name:
        raise ValueError("Participant name is empty.")

    subject = template["subject"].replace("[Name]", name)
    body = template["body"].replace("[Name]", name)
    signature = template["signature"].replace("[Name]", name)

    if signature.strip():
        body += "\n\n" + signature.strip()

    return {
        "subject": subject,
        "body": body,
    }


def validate_template(template):
    if not isinstance(template, dict):
        raise ValueError("The template must contain subject, body, and signature.")

    for field in ("subject", "body", "signature"):
        if field not in template:
            raise ValueError(f"Template is missing '{field}'.")

        if not isinstance(template[field], str):
            raise ValueError(f"Template '{field}' must be text.")

    if not template["subject"].strip():
        raise ValueError("Please enter an email subject.")

    if "\n" in template["subject"] or "\r" in template["subject"]:
        raise ValueError("The email subject must be a single line.")

    if not template["body"].strip():
        raise ValueError("Please enter an email message.")

def save_template(file_path, template):
    validate_template(template)

    template_data = {
        "subject": template["subject"],
        "body": template["body"],
        "signature": template["signature"],
    }

    Path(file_path).write_text(
        json.dumps(template_data, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

def load_template(file_path):
    template = json.loads(
        Path(file_path).read_text(encoding="utf-8")
    )

    validate_template(template)

    return {
        "subject": template["subject"],
        "body": template["body"],
        "signature": template["signature"],
    }

if __name__ == "__main__":
    example_template = {
        "subject": "Your workshop certificate",
        "body": (
            "Dear [Name],\n\n"
            "Thank you for attending our workshop.\n"
            "Please find your certificate attached."
        ),
        "signature": "Best regards,\nEvents Team",
    }

    example_participant = {
        "name": "John Tan",
        "email": "john@example.com",
        "certificate": "C:/Certificates/John Tan.pdf",
    }

    message = personalise_template(
        example_template,
        example_participant,
    )

    print("Subject:", message["subject"])
    print()
    print(message["body"])