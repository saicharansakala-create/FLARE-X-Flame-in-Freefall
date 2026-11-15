# FLARE-X Scientific Upgrade

Local FastAPI + SQLite backend for the supplied `flame_in_freefall_challenge(1).html` frontend.

## What is integrated
- The exact frontend research JSON datasets are indexed in SQLite: 24 investigations, 20 experimental-condition rows, 14 accidents, 66 accident timeline rows, 55 damaged-component rows, 18 temperature records, 21 combustion phenomena, 13 physics references, 10 mechanisms, 7 propellant records, 136 prevention measures, and supporting sources.
- The uploaded Excel workbook is imported sheet-by-sheet into SQLite (`Accidents`, `Timeline`, `Damaged_Components`, `PSI_Combustion`, `Sources`). README/Summary sheets are documentation/summary, not scientific record tables.
- Mission relevance endpoint reproduces the frontend's weighted feature-score formula and its habitat weights. It is a heuristic ranking, not a trained AI model or fire-risk probability.
- Local evidence assistant uses TF-IDF retrieval and extractive synthesis with source links. It is deliberately transparent and does not claim to be a cloud LLM.
- Validation endpoint reruns dataset integrity checks and Wien displacement arithmetic, reporting formulas, inputs, outputs and limitations.
- Upload endpoint analyses user-supplied CSV/XLSX with descriptive statistics, correlations, optional linear trends and a SHA-256 input fingerprint.
- Mission-specific safety brief ties findings to conditional design considerations; it is not a certified design or operational procedure.

## Scientific limits
The supplied workbook has a PSI combustion catalogue, not a complete raw synchronized flame/temperature time-series dataset. The frontend's 18 temperature entries mix measured, computed and theoretical records. Consequently this release validates internal consistency and selected equations, but does not claim a validated flame-spread, extinction-limit, CFD or fire-probability predictor. Upload suitable raw measurements before fitting or validating such a model.

## Run (Windows PowerShell)
From the project root, open two VS Code terminals.

Terminal 1:
```powershell
cd backend
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:
```powershell
py -m http.server 5500 --directory frontend
```

Open http://127.0.0.1:5500/flame.html . API docs: http://127.0.0.1:8000/docs .

SQLite is initialized automatically at first backend start. Do not run the frontend by double-clicking the HTML file; serve it over localhost.

## Main endpoints
- `GET /api/health`
- `GET /api/datasets/summary`
- `GET /api/data/{dataset}/{collection}`
- `GET /api/workbook/{sheet}`
- `GET /api/mission/rank?habitat=Moon%20base`
- `POST /api/assistant/ask` with `{"question":"..."}`
- `GET /api/validation/report`
- `GET /api/analysis/temperature`
- `POST /api/analysis/upload` (multipart CSV/XLSX; optional `time_column`)
- `GET /api/recommendations?habitat=Moon%20base`

### Optional local generative AI
The assistant works immediately in local retrieval mode. To enable a locally hosted generative model without a paid API:
1. Install Ollama on your computer and download a model suitable for your hardware.
2. In PowerShell, before starting Uvicorn, set ` $env:OLLAMA_MODEL="your-installed-model-name" `.
3. Optionally set ` $env:OLLAMA_URL="http://127.0.0.1:11434" `.
4. Start the backend. The assistant retrieves project evidence first, then passes only those retrieved excerpts to Ollama. If Ollama is unavailable, it falls back to extractive retrieval.

The model output is still advisory. Citations refer to retrieved records, so verify each cited primary source before relying on a generated interpretation.
