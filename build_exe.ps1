$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $oauthConfigPath = Join-Path $env:LOCALAPPDATA 'CertificateEmailAutomation\credentials.json'
    if (-not (Test-Path -LiteralPath $oauthConfigPath)) { throw 'Desktop OAuth credentials.json is required on the build computer.' }
    $oauthConfig = Get-Content -LiteralPath $oauthConfigPath -Raw | ConvertFrom-Json
    if (-not $oauthConfig.installed.client_id) { throw 'Use a Desktop OAuth client configuration.' }
    python -m PyInstaller --noconfirm --windowed --onedir --name CertificateMailer --collect-data customtkinter --collect-data googleapiclient --add-data "${oauthConfigPath};oauth" desktop_launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    Copy-Item -LiteralPath 'EXE_README.txt' -Destination 'dist/CertificateMailer/README.txt'
} finally {
    Pop-Location
}
