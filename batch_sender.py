import math
import re
from send_log import SendLog
from pathlib import Path

from email_templates import personalise_template, validate_template
from gmail_service import send_certificate_email

def prepare_email_jobs(participants, template):
    validate_template(template)

    if not participants:
        raise ValueError("There are no participants to send to.")

    jobs = []
    errors = []
    seen_emails = set()
    seen_certificates = set()

    for row_number, participant in enumerate(participants, start=1):
        name = participant.get("name", "").strip()
        email = participant.get("email", "").strip()
        certificate = participant.get("certificate")

        if not name:
            errors.append(f"Participant {row_number}: missing name.")
            continue

        # Basic format check; this does not verify mailbox ownership.
        if not re.fullmatch(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+", email):
            errors.append(f"{name}: invalid or missing email address.")
            continue

        if not certificate:
            errors.append(f"{name}: no matched certificate.")
            continue

        path = Path(certificate).resolve()

        if not path.is_file() or path.suffix.lower() != ".pdf":
            errors.append(f"{name}: certificate PDF does not exist.")
            continue

        email_key = email.casefold()

        if email_key in seen_emails:
            errors.append(f"{name}: repeated email address {email}.")
            continue

        if path in seen_certificates:
            errors.append(f"{name}: certificate is assigned more than once.")
            continue

        seen_emails.add(email_key)
        seen_certificates.add(path)

        message = personalise_template(template, participant)

        jobs.append({
            "name": name,
            "recipient": email,
            "subject": message["subject"],
            "body": message["body"],
            "certificate_path": str(path),
        })

    if errors:
        raise ValueError(
            "Resolve these issues before starting:\n\n"
            + "\n".join(errors)
        )

    return jobs

def send_batches(
    service,
    jobs,
    progress_queue,
    stop_event,
    *,
    batch_size=10,
    message_delay=2,
    batch_pause=30,
    dry_run=True,
    campaign_id=None,
):
    if not isinstance(batch_size, int) or isinstance(batch_size, bool):
        raise ValueError("Batch size must be a whole number.")

    if batch_size < 1:
        raise ValueError("Batch size must be at least 1.")

    for label, value in (
        ("Message delay", message_delay),
        ("Batch pause", batch_pause),
    ):
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{label} must be a finite, non-negative number.")
        
    if not dry_run and service is None:
        raise ValueError("Connect Gmail before sending.")
    
    if not dry_run and (
        not isinstance(campaign_id, str)
        or not campaign_id.strip()
    ):
        raise ValueError("A campaign ID is required for real sending.")

    if not dry_run:
        campaign_id = campaign_id.strip()

    send_log = None if dry_run else SendLog()

    # Copy the job dictionaries so the caller cannot edit this run's data.
    jobs = [dict(job) for job in jobs]

    total = len(jobs)
    processed = 0

    def report(event_type, **details):
        progress_queue.put({
            "type": event_type,
            **details,
        })

    def finish(reason):
        report(
            "finished",
            reason=reason,
            processed=processed,
            total=total,
            dry_run=dry_run,
        )

    report("started", total=total, dry_run=dry_run)

    for index, job in enumerate(jobs, start=1):
        if stop_event.is_set():
            finish("stopped")
            return

        report(
            "sending",
            index=index,
            total=total,
            recipient=job["recipient"],
        )

        # Check the file again in case it disappeared after preparation.
        if not Path(job["certificate_path"]).is_file():
            report(
                "failed",
                recipient=job["recipient"],
                error="Certificate file no longer exists.",
            )
            finish("error")
            return

        if dry_run:
            report(
                "simulated",
                index=index,
                recipient=job["recipient"],
            )

        else:
            # Record the attempt before contacting Gmail.
            try:
                should_send = send_log.claim(campaign_id, job)
            except Exception as error:
                report(
                    "failed",
                    recipient=job["recipient"],
                    error=str(error),
                )
                finish("review_required")
                return

            # A matching confirmed send already exists.
            if not should_send:
                processed += 1

                report(
                    "skipped",
                    index=index,
                    recipient=job["recipient"],
                    reason="Previously confirmed as sent.",
                )
                continue

            try:
                message_id = send_certificate_email(
                    service,
                    job["recipient"],
                    job["subject"],
                    job["body"],
                    job["certificate_path"],
                )

            except Exception as error:
                error_text = str(error)

                try:
                    send_log.record(
                        campaign_id,
                        job["recipient"],
                        "unconfirmed",
                        error=error_text,
                    )
                except Exception as log_error:
                    # The saved 'sending' record still blocks resending.
                    error_text += (
                        f"\nCould not save the error: {log_error}"
                    )

                report(
                    "unconfirmed",
                    recipient=job["recipient"],
                    error=error_text,
                )
                finish("review_required")
                return

            # Gmail accepted the email. Save its message ID.
            try:
                send_log.record(
                    campaign_id,
                    job["recipient"],
                    "sent",
                    message_id=message_id,
                )
            except Exception as error:
                report(
                    "unconfirmed",
                    recipient=job["recipient"],
                    error=(
                        f"Gmail accepted message {message_id}, "
                        f"but saving the result failed: {error}"
                    ),
                )
                finish("review_required")
                return

            report(
                "sent",
                index=index,
                recipient=job["recipient"],
                message_id=message_id,
            )

        processed += 1

        # There is no need to pause after the final message.
        if index == total:
            continue

        if index % batch_size == 0:
            pause_seconds = batch_pause
            pause_reason = "between_batches"
        else:
            pause_seconds = message_delay
            pause_reason = "between_messages"

        report(
            "waiting",
            seconds=pause_seconds,
            reason=pause_reason,
        )

        if stop_event.wait(pause_seconds):
            finish("stopped")
            return

    finish("completed")

