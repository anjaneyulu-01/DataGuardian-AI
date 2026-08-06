# One-time local setup for Windows / PowerShell.
#   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# One .env at the repository root configures the backend, the frontend, and
# docker-compose. Create it first so both installs see it.
Write-Host '==> Root: environment file' -ForegroundColor Cyan
Set-Location $root
if (-not (Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Host '    created .env from .env.example' -ForegroundColor DarkGray
} else {
  Write-Host '    .env already exists, leaving it alone' -ForegroundColor DarkGray
}

Write-Host '==> Backend: creating virtual environment (Python 3.12)' -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path '.venv')) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt

Write-Host '==> Frontend: installing npm dependencies' -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install

Write-Host ''
Write-Host 'Setup complete.' -ForegroundColor Green
Write-Host '  Backend:  cd backend;  .\.venv\Scripts\Activate.ps1;  uvicorn app.main:app --reload'
Write-Host '  Frontend: cd frontend; npm run dev'
