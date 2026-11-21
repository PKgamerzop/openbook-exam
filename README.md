# openbook-exam

OpenBook is a computer-based open-book examination platform. The starter runs a React and TypeScript welcome screen, a FastAPI health endpoint, and a local PostgreSQL database.

## Windows setup

Install Node.js 24 LTS, Python 3.14, and Docker Desktop with the Docker Compose plugin and Linux containers enabled. Start Docker Desktop and wait for the engine to be ready. If Docker Desktop asks you to enable WSL 2 or restart Windows, complete that setup first.

Run the following from the repository directory that contains this README in PowerShell. Set a local development password in `.env` before starting PostgreSQL.

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up -d --wait db
```

If port 5432 is already in use, change `POSTGRES_PORT` in `.env` before starting Compose. The database uses a named volume. Once initialized, changing the credentials in `.env` alone does not change the database credentials.

### Start the API

Run this from the repository root in one PowerShell window. The commands use the virtual environment's Python directly, so PowerShell script activation is optional.

```powershell
py -3.14 -m venv .venv
Set-Location backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The baseline revision initializes Alembic's migration tracking. The health endpoint at `http://127.0.0.1:8000/api/health` returns HTTP 200 when a database query succeeds and HTTP 503 when the API is running but cannot query PostgreSQL.

### Start the frontend

Open another PowerShell window at the repository root.

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://127.0.0.1:5173` to see the welcome screen and connection status. Vite forwards `/api` to the API on port 8000 for development and local preview. Use **Check again** after starting or restoring a service. A deployed static build needs equivalent same-origin routing for `/api`.

To stop local services, press Ctrl+C in both windows and run `docker compose down` from the repository root. The database volume persists.

## Checks

Run these from the repository root after installing dependencies.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m ruff format --check .
..\.venv\Scripts\python.exe -m pytest
Pop-Location

Push-Location frontend
npm.cmd run lint
npm.cmd test
npm.cmd run build
Pop-Location
```

GitHub Actions runs the same checks and verifies the baseline migration and health endpoint against PostgreSQL. See the [product specification](docs/product-spec.md), [architecture](docs/architecture.md), and [roadmap](docs/roadmap.md) for planned features.
