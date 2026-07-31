# One-time local setup for Windows / PowerShell.
#   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host '==> Backend: creating virtual environment (Python 3.12)' -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path '.venv')) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }

Write-Host '==> Frontend: installing npm dependencies' -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install
if (-not (Test-Path '.env.local')) { Copy-Item '.env.example' '.env.local' }

Write-Host '==> Root: compose environment file' -ForegroundColor Cyan
Set-Location $root
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }

Write-Host ''
Write-Host 'Setup complete.' -ForegroundColor Green
Write-Host '  Backend:  cd backend;  .\.venv\Scripts\Activate.ps1;  uvicorn app.main:app --reload'
Write-Host '  Frontend: cd frontend; npm run dev'
