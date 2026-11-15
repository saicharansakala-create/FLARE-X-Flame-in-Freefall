$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python 3.10+ is required. Install Python and enable Add Python to PATH." }
if (-not (Test-Path ".venv")) { py -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
