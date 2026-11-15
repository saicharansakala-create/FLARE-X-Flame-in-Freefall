$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "frontend")
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python 3.10+ is required. Install Python and enable Add Python to PATH." }
Start-Process "http://127.0.0.1:5500/flame.html"
py -m http.server 5500 --bind 127.0.0.1
