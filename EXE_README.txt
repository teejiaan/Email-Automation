Certificate Mailer — Windows

Run CertificateMailer.exe. Keep the _internal folder beside it.
Copy the entire CertificateMailer folder to another Windows computer; Python is not required.

Google setup on another computer:
The Desktop OAuth configuration is included. No manual JSON copying or folder creation is needed.
Open the app, click Connect with Google, and choose your account to approve access.
Existing Google OAuth testing/authorisation restrictions still apply.

Login tokens and send history are created automatically in
%LOCALAPPDATA%\CertificateEmailAutomation, outside this application.
They are not included in this distribution. Another device starts with separate history;
it cannot automatically skip messages sent on the original device.
Select Excel/PDF files available on the new device.

Build again after source changes:
python -m pip install -r requirements.txt
python -m pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build_exe.ps1

The package is not code-signed. Initial validation covers offline UI startup only;
complete Google sign-in and a dry run on the destination computer before sending.
