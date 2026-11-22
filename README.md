# openbook-exam

OpenBook is a computer-based open-book examination platform. Lecturers author and publish MCQ exams. Assigned students can review the rules and start a single attempt during the scheduled window.

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
..\.venv\Scripts\python.exe -m app.seed
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Revision 0002 adds the core exam schema. The seed command prompts privately for local passwords for `lecturer` and `student` and preserves existing accounts. For an older local HTTP setup, add `OPENBOOK_LOCAL_HTTP=1` to the ignored .env. HTTPS deployments use secure cookies by default. The health endpoint at `http://127.0.0.1:8000/api/health` returns HTTP 200 when a database query succeeds and HTTP 503 when the API is running but cannot query PostgreSQL.

### Start the frontend

Open another PowerShell window at the repository root.

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://127.0.0.1:5173` to see the welcome screen and connection status. Vite forwards `/api` to the API on port 8000 for development and local preview. Use **Check again** after starting or restoring a service. A deployed static build needs equivalent same-origin routing for `/api`.

### Verify the connection

With all three services running, run `Invoke-RestMethod http://127.0.0.1:8000/api/health` in PowerShell. Expect `status: ok` and `database: available`. The welcome screen should show **API and database connected**.

To check the API outage state, stop Uvicorn with Ctrl+C and select **Check again**. The welcome screen should show **API health check unavailable**. To check the database outage state, keep Uvicorn running and run `docker compose stop db` from the repository root. After retrying, expect **API connected. Database unavailable.** Restore the database with `docker compose up -d --wait db`.

To stop local services, press Ctrl+C in both windows and run `docker compose down` from the repository root. The database volume persists.

## Exercise Phase 2

1. Sign in as `lecturer`, create a course, and enroll `student` by username.
2. Create a draft. Enter instructions, permitted-resource rules, opening and closing times in your local timezone, and a duration. For a short rehearsal, choose an opening a few minutes ahead. Select the enrolled student.
3. Add an MCQ with two options, select its correct option and enter a topic. Save, preview, then select **Validate and publish**. The published preview shows the effective revision even if you later save a different draft.
4. Sign out and sign in as `student`. Open the assigned exam and read the rules. At opening, refresh availability and start. Return to the list and start again during the active attempt to verify the same attempt and deadline.

## Exercise Phase 3

Apply the migrations and install the backend and frontend dependencies using the Windows setup above. From the repository root, start the indexing worker in its own PowerShell window alongside FastAPI, PostgreSQL and Vite.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m app.reference_worker
```

Initialize the local demonstration from the **repository root** after migration. The coordinator generates the original PDF fixtures, provisions the lecturer and students, publishes both exams and finishes indexing before returning.

```powershell
.\scripts\Initialize-Demo.ps1 -Development
```

The coordinator generates a shared random password for these seven fictional accounts and encrypts it for the current Windows user using DPAPI. To copy it locally for sign-in, run the following from the repository root. Clear the clipboard after the walkthrough.

```powershell
$demoSecret = ConvertTo-SecureString (Get-Content -Raw .local-demo/credential.dpapi)
([PSCredential]::new('demo_lecturer', $demoSecret)).GetNetworkCredential().Password | Set-Clipboard
```

| Account | Assignment |
| --- | --- |
| `demo_lecturer` | Owns Database Management Systems, Computer Science Engineering — Semester 5 |
| `demo_student_01`, `demo_student_02` | Exam A |
| `demo_student_03`, `demo_student_04` | Exam B |
| `demo_student_05` | Both exams, each with a distinct reference list |
| `demo_student_06` | Enrolled, neither exam |

1. As the lecturer, open the DBMS course and **Reference Library**. Inspect the four two-page guides and preview **Scan**, the image-only document. Upload a local PDF, refresh its processing state, then organize it by folder and topics. Choose **New version of** to retain an earlier edition. A failed job exposes **Retry indexing**.
2. Open an upcoming draft and select specific editions under **Permitted PDF versions**. Save, then validate and publish. Explicit pre-release allows assigned students to read before opening. During the scheduled window, both policies require a live attempt.
3. As student 05, open Exam A and start it. Search for `deadlock`, click the result and check the viewer opens **Transactions Guide, page 2**. Return to assigned exams and open upcoming Exam B. Search for `hashjoin` to open **Query Optimization, page 2**. Searching the opposite exam for either term yields no matches.
4. Sign in as student 06 and check the empty exam list. Students 01 and 03 each see only their assigned exam. The API tests also request the other exam directly, including its metadata, snippets and byte ranges.

| Exam | PDF | Canonical query and expected one-based pages |
| --- | --- | --- |
| A | indexing-guide.pdf | `leaf` (1, 2) |
| A | transactions-guide.pdf | `snapshot` (1), `deadlock` (2) |
| B | query-optimization.pdf | `cardinality` (1), `hashjoin` (2) |
| B | normalization-guide.pdf | `dependency` (1), `decomposition` (2) |

A opens one hour before initial setup and B opens 24 hours afterward. Each window lasts two days. A rerun preserves credentials, dates, immutable versions and attempts. Preserve the encrypted credential file with this local environment. For a fresh schedule, use a fresh development database and a separate private storage directory. Seeding requires loopback, `OPENBOOK_LOCAL_HTTP=1`, and the database name `openbook` or `openbook_demo`. Existing unrelated usernames cause a rollback. The classroom seed and its publication clock are local utilities.

### Storage and recovery

Set `OPENBOOK_PDF_DIR` to an absolute private directory shared by the API and worker, or use the repository's ignored `.private-pdfs` directory. Restrict OS access to the service user. The default upload limit is 20 MiB (`OPENBOOK_PDF_MAX_BYTES`) and 200 pages (`OPENBOOK_PDF_MAX_PAGES`). Restart both processes after changing configuration. Encrypted and malformed files are rejected. Image-only PDFs are readable. Search uses extracted text and has no OCR.

Restart the worker with the same command after interruption. A job becomes claimable after its 90-second lease expires. Each parse has a 30-second deadline and a monitored 384 MiB process memory limit. Accepted extraction output is bounded to 100,000 characters per page and two million per document. Repeated processing failures appear in the lecturer library. Inspect disk availability, file permissions and limits before retrying.

Quiesce uploads and the worker for a coordinated PostgreSQL backup and private-directory snapshot. Restore both from the same point. Migration 0003 adds tables and a GIN index, with no rewrite of prior exam or attempt rows. Downgrading to 0002 discards reference bindings, jobs and indexes. Disk files remain private. Restore the matching backup to recover bindings before serving Phase 3 again. An interrupted upload can leave an unreferenced private file. Reconcile against stored UUIDs with services stopped before any manual cleanup.

## Exercise Phase 4

From the repository directory, apply migration 0004 in the backend and initialize the Phase 3 demo if it is new. Then create the Phase 4 rehearsals.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location
.\scripts\Initialize-Demo.ps1 -Development
Push-Location backend
..\.venv\Scripts\python.exe -m app.rehearsal --development
Pop-Location
```

Start the API, frontend and PDF worker as above. In another PowerShell window at the repository root, start automatic expiry processing.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m app.attempt_expiry
```

Use the Phase 3 demo credentials. Sign in as `demo_student_05` and open **DBMS Rehearsal — Timed workspace**. The 15-minute exam enables the calculator. Answer one of the ten questions, flag another, write a scratchpad note and pin a PDF page. Wait for **Saved** and reload the page. The answers, flags, note, and saved pages should return. Keep a question unanswered, open **Review and submit**, and verify the counts before confirming. The receipt reports the recorded answer count.

Use **DBMS Rehearsal — Calculator disabled** for the two-minute expiry case. Save an answer and let the timer reach zero. The expiry receipt records saved answers. To rehearse reconnection, take the browser offline after the workspace loads, edit a response and check for **Save failed**. Reconnect and use **Retry saves** while the time window remains open. Each seed run reuses the same rehearsal exams and preserves attempts.

Deployments need same-origin API routing and an SPA fallback that serves `index.html` for frontend routes such as `/courses/123` and `/exams/123`. Keep `/api` and asset paths outside that fallback. Connection diagnostics are available on the sign-in page.

## Exercise Phase 5 results on Windows

Use the same development database and accounts as Phases 3 and 4. From the repository root, apply the migration and seed the results cases.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location
.\scripts\Initialize-Demo.ps1 -Development
Push-Location backend
..\.venv\Scripts\python.exe -m app.results_demo --development
Pop-Location
```

Start the API, frontend and expiry worker using the existing commands. Sign in as `demo_lecturer`, open the DBMS course and select **DBMS Results — Awaiting release**. Open **View exam results**. Expect five graded attempts, one student who never started, an average of 2.2/5, and scores of 0, 1, 2, 3 and 5. Review an attempt before confirming release. Sign in as `demo_student_01` and open **My results** to see 5/5 and the five explanations. Student 06 sees no attempt. **DBMS Results — Released** is published by the seed for an immediate walkthrough.

Release is irreversible through the application and requires exam close plus complete grading of all started attempts. A pending expired attempt is processed by the expiry worker. Re-running the seed reuses both exams and preserves prior work.

## Checks

Run these from the repository root after installing dependencies.

```powershell
Push-Location frontend
npm.cmd run lint
npm.cmd test
npm.cmd run build
Pop-Location

Push-Location backend
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m ruff format --check .
$env:OPENBOOK_TEST_POSTGRES = '1'
$env:OPENBOOK_TEST_BROWSER = '1'
..\.venv\Scripts\python.exe -m pytest
Pop-Location
```

The integration suite needs PostgreSQL and permission to create temporary schemas. Each run exercises upgrade, downgrade and re-upgrade within its own schema. The browser check uses installed Google Chrome and the frontend build. CI runs both suites and checks the live health endpoint. The [PDF search experiment](experiments/pdf-search/README.md) has its own dependencies and runs separately.

See the [product specification](docs/product-spec.md), [architecture](docs/architecture.md), and [roadmap](docs/roadmap.md) for planned features. The [Phase 1 progress log](docs/phase-1-progress.md) records verification evidence by issue.
