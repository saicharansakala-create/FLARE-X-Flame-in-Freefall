# FLARE-X — integrated frontend + backend

This package uses the latest supplied `flametabbed.html` as the frontend and the local FastAPI/SQLite backend. The Mission Intelligence panel calls the backend for dataset status, mission ranking, habitat-aware AI research answers, validation, temperature analysis, uploads and mission-specific recommendations.

## Requirements
- Windows 10/11
- Python 3.10+
- Internet access on first launch to install Python dependencies

## One-click startup
1. Extract the ZIP completely.
2. Open the `FLAREX_Scientific_Upgrade` folder.
3. Double-click `START_FLAREX.bat`.
4. Keep both server terminal windows open.
5. Open `http://127.0.0.1:5500/flame.html` if the browser does not open automatically.

## VS Code manual startup
Open the extracted project folder in VS Code.

Terminal 1 — backend:
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:
```powershell
cd frontend
py -m http.server 5500 --bind 127.0.0.1
```

Frontend: http://127.0.0.1:5500/flame.html  
API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/health

## Mission Intelligence + AI assistant
- The frontend sends the selected habitat with every AI question.
- `/api/assistant/ask` retrieves relevant evidence from the indexed local project data and includes the top investigations from the same habitat-weighted ranking used by `/api/mission/rank`.
- Default AI mode is local TF-IDF retrieval plus extractive synthesis. It runs without an external API key.
- Optional local Ollama generation: install/run Ollama, pull a model, then set `OLLAMA_MODEL` (and optionally `OLLAMA_URL`) in the backend terminal before starting Uvicorn. Example:
```powershell
$env:OLLAMA_MODEL="llama3.2:3b"
$env:OLLAMA_URL="http://127.0.0.1:11434"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
If Ollama is unavailable, the assistant automatically falls back to evidence extraction. The assistant must not be treated as an engineering certification system.

## Sharing with teammates
Share the complete ZIP, not just `flame.html`. Each teammate runs the app locally. `127.0.0.1` refers to the same computer and is not a public URL. For LAN access, host binding, CORS and firewall settings must be configured deliberately; do not expose the development server directly to the public internet.
