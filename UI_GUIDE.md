# Certificate Mailer desktop redesign

Run `python app.py`. Install dependencies with `python -m pip install -r requirements.txt` if needed.

## Account page

The app checks a saved session in the background. Select **Connect with Google** if no valid session is available. The new profile feature requests OpenID, email and profile permission as well as Gmail sending permission. An older send-only token requires fresh consent. There is no need to delete credentials.json.

The account card shows the sender's name, email and profile photo (initials if unavailable). Continue opens the workspace. **Use another account** opens Google's account chooser. Cancelling a switch leaves the previous usable account intact.

## Workspace

Select the Excel file and certificate folder, check matches, compose or load a template, and preview individual recipients with the arrow controls. Multiple PDFs matching one normalised name are flagged rather than silently selecting the first file.

The preview and expandable activity log are separate. The footer keeps progress, test, dry-run, stop, and review/send controls visible while the content scrolls. Tests send to the connected sender account. Dry runs send nothing.

Real sending opens a review containing the exact recipient, subject, message and PDF path for each email, and requires typing the campaign name. The previous three-recipient live-test limit is retained. Pacing remains 10 per batch, 2 seconds between messages, and 30 seconds between batches.

## Account menu and logout

Select the avatar in the top-right for the display name, email, **Log out**, and **Quit**. Logout removes only this application's token and clears its loaded recipients. Saved templates, OAuth client configuration and send history remain. It does not sign out the browser or revoke the Google grant. Logout is blocked during an operation; quitting during a batch requests a stop and waits for the current request to finish.

## Send history

New campaigns are namespaced by the stable Google account ID. The existing SQLite schema and older records are preserved. If a recipient has an older record under the same campaign name without a known sender, sending stops for review instead of silently ignoring that record. Do not choose a different campaign name merely to bypass a previous send.

## Offline checks

`python -m unittest test_batch_integration test_account_flow test_ui_flow -v`

The tests use fake senders, fictional profiles and temporary databases. GUI tests instantiate local windows without authenticating. `preview_ui.py` captures fictional-account screenshots and closes automatically; it never sends email.

Live Google profile retrieval must be checked by signing in yourself. No live authorisation or email sending was performed during implementation.
