$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

Start-Process powershell -WindowStyle Normal -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$Backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)

Start-Process powershell -WindowStyle Normal -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$Frontend'; npm run dev -- --host 127.0.0.1"
)

Write-Host "ResearchOS local site:"
Write-Host "  Frontend: http://127.0.0.1:5173/"
Write-Host "  Backend:  http://127.0.0.1:8000/"
Write-Host "  API docs: http://127.0.0.1:8000/docs"
