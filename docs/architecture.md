# Architecture

Use a modular monolith built around one React and TypeScript frontend, one FastAPI application, and PostgreSQL. Run PDF processing as a worker from the same backend codebase. PostgreSQL stores application data, PDF page text, and jobs. Private file storage holds original PDFs under opaque identifiers.

## Future directory structure

```text
frontend/
  src/
    app/
    features/
      authoring/
      exam/
      references/
      results/
backend/
  app/
    access/
    authoring/
    attempts/
    references/
    ai_assistance/
  migrations/
  tests/
docs/
AGENTS.md
```

Group routes, validation, and feature logic together. Put grading and result release in the attempts module. Put file delivery, indexing, and search in references. Share database configuration and authentication plumbing across modules. Keep feature queries close to their callers and introduce shared helpers when they have multiple concrete uses.

## Exam and attempt lifecycle

- **Authoring and opening (L01–L04).** Store exams, ordered questions and options, topic tags, optional learning objectives, rules, and exam access assignments. Publishing validates the exam and creates a scheduled revision. Allow revisions before opening. At the opening boundary, use the published revision as the immutable source of questions, grading keys, rules, opening and closing times, and permitted PDF versions. Prevent edits or deletion from changing what students see during the exam.
- **Starting and saving (S01, S05–S07).** The API checks identity, assignment, and the server-side exam window before creating an attempt. A unique database constraint enforces one attempt per exam and student. Use UTC timestamps and return the deadline to the client for display in local time. Persist answers and flags by question and one scratchpad per attempt. Serialize saves for each question in the frontend, and keep pending edits visible until acknowledged. Restore server-saved state on refresh.
- **Submitting and expiring (S07, L06).** Serialize answer writes and finalization on the attempt row. Check deadlines with the server clock after acquiring the lock so queued late saves are rejected. Finalize a timely submission within one transaction. A scheduled backend job finalizes overdue attempts through the same operation and can resume after failure. Repeated submission requests return the stored submission status. A transaction persists the terminal attempt state and its grading result together once grading is available.
- **Grading, feedback, and reporting (L06–L07, S08).** Compute scores using the frozen question set and answer key. Authorized lecturers review finalized grades and feedback, then explicitly release the results. Student responses expose only submission status before release and the student's own released result afterward. Aggregate finalized attempts for exam-, question-, and topic-level reports.

## PDF delivery and search

- **Upload and indexing (L03).** Validate the uploader's authorization and enforce file size and processing limits. Store originals privately and create an indexing job in PostgreSQL. The worker claims jobs with a lease, extracts text page by page under time and resource limits, and publishes page records and their search vectors atomically. Expired leases permit recovery after worker failure. Retrying an index job for a PDF version replaces its page index without duplicating rows. Report indexing status and failures to the lecturer.
- **Viewing and search (S02–S04).** PDF.js opens PDFs through an authenticated endpoint that supports byte-range reads. Check student assignment, attempt ownership and active exam access, and permitted PDF version for every file or search request. Apply those checks before returning metadata, file content, or search snippets. PostgreSQL full-text search runs over page text with a GIN index on search vectors. Return the document identifier, one-based page number, and a plain-text snippet so the viewer can jump to the hit. A valid PDF with no extractable text is view-only. Store bookmarks and pins under the attempt and validate their PDF version and page on write.

### Phase 3 implementation

The course owns logical documents with a folder label and topic array. Each upload appends an immutable edition with a title, original filename, UUID storage key and page count. PostgreSQL foreign keys retain editions that published revisions depend on. Existing JSONB drafts default to an empty selection and restricted release.

The raw upload route verifies course ownership, bounds streamed input and validates the PDF in a subprocess. The worker uses pypdf 7.1.1 (BSD-3-Clause, compatible with Python 3.14) and psutil for process monitoring. Jobs use PostgreSQL row locks, SKIP LOCKED, expiring leases and unique claim tokens. A worker publishes pages, updates status and retires its claim in one transaction. A replaced claim cannot publish stale results. One-based page numbers map directly to PDF.js navigation.

The same exam access function guards the student list, search and file delivery. Pre-release ends at opening. Access then requires an attempt for that revision before its deadline and exam closing. Each byte-range request goes through the same checks. Students receive a narrow metadata projection. The search query uses the simple PostgreSQL dictionary, a stored tsvector, a GIN index and stable rank/version/page ordering. The React viewer renders snippets as text and destroys loading and render tasks on switch. See the [development walkthrough and recovery instructions](../README.md#exercise-phase-3).

## Security and optional AI

### Core examination pilot

Local accounts use per-user random salts and scrypt (N=131072, r=8, p=1). Database-backed sessions allow immediate logout and avoid a client-held bearer token in JavaScript. The browser holds an opaque 256-bit random token in an HttpOnly, SameSite=Strict cookie scoped to /api. The database holds its SHA-256 digest and an eight-hour expiry. Login rotates the current browser session. Mutations require a custom header, cross-site browser mutations are rejected, and the API enables no cross-origin access. Serve the application and API on the same HTTPS origin. Loopback development can explicitly enable HTTP cookies. Institutional SSO remains a deployment decision.

Courses belong to one lecturer. Lecturers enroll existing students by username. Course-scoped catalog entries retain reusable topic and objective names. The ordered MCQs, options, single correct index, tags, one-point rule, policy settings and candidate assignments are validated together as a draft and stored as JSONB. Each publication copies that aggregate to a new revision and materializes its assigned students as indexed relational rows. A composite foreign key ties each attempt to an assigned revision. A unique constraint limits each student to one attempt per exam.

The API locks the exam row and checks both the expected edit number and the effective revision's opening time before replacing a draft or publishing. Drafts can be incomplete. Publication requires instructions, resource rules, a positive duration, a future opening before closing, an eligible assignment and a valid question set. The active revision stays effective until explicitly republished. At opening it becomes final without depending on a scheduled job. Student endpoints project permitted fields explicitly. The start transaction rechecks assignment and UTC time after locking and returns the stored attempt on eligible retries. Its deadline is the earlier of exam closing and start plus duration.

Migration 0002 adds tables to the empty 0001 baseline and needs no backfill. Downgrading to 0001 removes Phase 2 data. Back up the database before any operational downgrade and restore that backup to recover populated records. The automated rollback check runs in a new disposable schema.

Authorize access in FastAPI on every protected route. Scope lecturer operations to the lecturer's exams and references. Scope student operations to the student's assignments and attempts. Exclude answer keys, other students' work, and unreleased results from student responses. Keep uploaded files private, use TLS in deployment, supply secrets through environment configuration, and log operational events without recording student answers, scratchpad text, or answer keys.

AI assistance (L05) is an optional lecturer action. Send only the lecturer-selected authored content needed for the request and exclude student data. Treat generated text as draft material. Applying it requires an explicit lecturer action, and publishing uses the normal exam workflow. A provider failure leaves saved content available for editing.

## Early feasibility checks

| Risk | Test and evidence |
| --- | --- |
| PDF extraction and viewer compatibility | Use text, multi-column, scanned, and malformed PDF fixtures. Record extracted text quality, page mapping, search-to-viewer jumps, and whether scanned and malformed files surface the expected statuses. |
| Reference isolation | Use two exams with different references and two assigned students. Verify a student cannot retrieve the other exam's file, bytes via range requests, metadata, or search snippets. |
| Exam timing and persistence | Simulate refresh, disconnect and retry, concurrent save and submit, duplicate submission, and a save waiting on a lock through expiry. Verify that one final result uses the eligible server-saved answers and subsequent writes are rejected. |
| Processing cost and peak load | Measure extraction time, index size, and search and answer-save latency. Test concurrent attempts while indexing representative PDFs. Record the corpus, concurrent attempt count, environment, latency percentiles, and observed failures. Use the results to set upload and pilot limits. |

See the [product specification](product-spec.md) for acceptance criteria and the [roadmap](roadmap.md) for the feasibility and pilot gates.
