$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.10+ and enable Add Python to PATH."
}
if (-not (Test-Path (Join-Path $Backend "app\main.py"))) {
    throw "Backend files are missing. Extract the complete FLARE-X folder first."
}
if (-not (Test-Path (Join-Path $Frontend "flame.html"))) {
    throw "frontend\flame.html was not found."
}

$BackendCommand = "Set-Location '$Backend'; if (-not (Test-Path '.venv')) { py -m venv .venv }; .\.venv\Scripts\python.exe -m pip install -r requirements.txt; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
$FrontendCommand = "Set-Location '$Frontend'; py -m http.server 5500 --bind 127.0.0.1"

Start-Process powershell -ArgumentList @("-NoExit","-ExecutionPolicy","Bypass","-Command",$BackendCommand)
Start-Process powershell -ArgumentList @("-NoExit","-ExecutionPolicy","Bypass","-Command",$FrontendCommand)
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5500/flame.html"
Write-Host "FLARE-X starting. Keep both terminal windows open."
