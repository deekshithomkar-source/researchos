$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$IpAddress = (Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
  Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $IpAddress) {
  throw "Could not detect a LAN IPv4 address."
}

Start-Process powershell -WindowStyle Normal -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$Backend'; `$env:ALLOWED_ORIGINS='http://$IpAddress`:5173,http://localhost:5173,http://127.0.0.1:5173'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
)

Start-Process powershell -WindowStyle Normal -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$Frontend'; `$env:VITE_API_URL='http://$IpAddress`:8000/api'; npm run dev:lan"
)

Write-Host "ResearchOS LAN site:"
Write-Host "  Frontend: http://$IpAddress`:5173/"
Write-Host "  Backend:  http://$IpAddress`:8000/"
Write-Host "  API docs: http://$IpAddress`:8000/docs"
