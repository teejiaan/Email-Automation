import json
import re
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


def variable_key(value):
    # [Event Date], [event_date] and [EVENT DATE] refer to the same column.
    return ' '.join(value.replace('_', ' ').split()).casefold()


def personalise_template(template, participant):
    validate_template(template)
    name = participant['name'].strip()
    if not name:
        raise ValueError('Participant name is empty.')
    values = {variable_key(key): value
              for key, value in template.get('variables', {}).items()}
    values.update({variable_key(key): value
                   for key, value in participant.get('variables', {}).items()
                   if value is not None and str(value).strip()})
    values.update({'name': name, 'email': participant.get('email', '')})

    def replace(match):
        label = match.group(1).strip()
        value = values.get(variable_key(label))
        if value is None or not str(value).strip():
            raise ValueError(f"{name}: missing value for [{label}]. Fill this field in Placeholders or Excel, or remove the placeholder.")
        return str(value).strip()

    # Substitute once, so brackets inside spreadsheet values remain literal.
    rendered = {field: re.sub(r'\[([^\[\]\r\n]+)\]', replace, template[field])
                for field in ('subject', 'body', 'signature')}
    validate_template(rendered)
    body = rendered['body']
    if rendered['signature'].strip():
        body += '\n\n' + rendered['signature'].strip()
    return {'subject': rendered['subject'], 'body': body}


def validate_template(template):
    if not isinstance(template, dict):
        raise ValueError("The template must contain subject, body, and signature.")

    variables = template.get('variables', {})
    if not isinstance(variables, dict) or any(
            not isinstance(key, str) or not variable_key(key)
            or not isinstance(value, str) for key, value in variables.items()):
        raise ValueError('Placeholder names and values must be text.')

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
        **({"variables": template["variables"]} if "variables" in template else {}),
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
        **({"variables": template["variables"]} if "variables" in template else {}),
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