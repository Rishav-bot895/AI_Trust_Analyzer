# AI_Trust_Analyzer

Basic setup instructions for running this project after cloning.

## Prerequisites

- Python 3.10+ installed
- Node.js 20+ installed
- npm (comes with Node.js)

## 1) Clone and enter the project

```bash
git clone <your-repo-url>
cd AI_Trust_Analyzer
```

## 2) Create and activate Python virtual environment

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Windows (CMD)

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3) Install backend Python dependencies

From the repository root:

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Do not use global Python for this project. Use this interpreter for all backend commands:

```text
.venv\Scripts\python.exe
```

## 4) Install frontend dependencies

```bash
cd frontend
npm install
```

## 5) Run frontend in development mode

```bash
npm run dev
```

Frontend will usually be available at:

```text
http://localhost:3000
```

## Helpful commands

From `frontend`:

```bash
npm run lint
npm run build
npm run start
```

## Notes

- Keep the virtual environment activated while working with Python dependencies.
- If you installed dependencies previously in a different environment, reinstall them inside `.venv`.
- Run backend tests with `.venv\Scripts\python.exe -m pytest`.