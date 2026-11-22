# Phase 6 progress

## Verified baseline

- Phase 5 PRs [#64](https://github.com/PKgamerzop/openbook-exam/pull/64) and [#65](https://github.com/PKgamerzop/openbook-exam/pull/65) merged into main. [CI run 45033564120](https://github.com/PKgamerzop/openbook-exam/actions/runs/45033564120) passed on b48e07dc4a9b9c78169246dcbee180aa79b8070b.
- GitHub issues #51–56 and #61 are closed for verified Phase 5 implementation. Human usability and AI evaluation remain visible on the relevant review records.
- All 14 Phase 6 issues and corresponding Notion tasks exist. See the [work package matrix](phase-6-plan.md) and [Development Tracker](https://app.notion.com/p/41f6a9609e1181e5a389c2d4e0a41f69).

## Staging work

- Windows Docker Desktop built the Linux images. Isolated loopback Compose startup completed, Alembic exited successfully, and PostgreSQL, API, indexer and expiry workers reached health.
- The Windows frontend lint, 10 unit tests and production build passed. The first PostgreSQL/browser invocation encountered Windows temporary-directory permissions. The rerun used a workspace-local base directory.
- AI provider integration and evaluation are deferred. Human review and deployment approval remain open.


## Local validation evidence

- Windows frontend lint, 10 tests and production build passed. The PostgreSQL and Chrome suite passed 35 tests. The isolated lifecycle/workspace/configuration rerun passed 19 checks after the database checkout fix, including 60 concurrent starts returning one attempt. The expanded supervised Chrome flow authored and published an exam, submitted the student answer and verified the lecturer grade.
- Trusted loopback HTTPS verified secure cookies, same-origin request handling, SPA fallback, private PDF ranges, expected released and unreleased grades, and AI-disabled API and bundle behavior.
- The 60-account pilot fixture reproduced its manifest without touching the existing demo database. Staging rendered a 120-page PDF with a selectable text layer. The Windows browser harness now serves the worker module with the correct MIME type.
- Persistent HTTPS at 30 students measured p95 of 395 ms for save and 396 ms for search. A failed 60-student attempt-start burst revealed thread starvation during database checkout. The 60-student retest completed with p95 of 590 ms for save and 560 ms for search, and all answers, grades and authorization checks matched expectations. [Performance report](performance-report.md)
- Backup and restore verified the same protected PDF digest, byte range, grade and result release states. Database outage left liveness at 200 and readiness at 503. After restart, readiness recovered and the restarted expiry worker graded one overdue synthetic attempt. [Recovery report](backup-and-recovery.md)
- Application dependency audits reported zero known vulnerabilities. Full image scanning and public certificate verification remain open. [Security review](security-review.md)
- [Draft PR #80](https://github.com/PKgamerzop/openbook-exam/pull/80) targets main. [Browser screenshots](phase-6-screenshots/README.md) support review. Human usability approval, host selection and institution authorization are open.

- A 120-page upload remained queued while the PDF indexer was stopped and became searchable after restart in 4.24 seconds including the status read. Chrome verified the narrow-screen reader and an authenticated PDF text layer. Bounded search results keep the reader near the top of the workspace.
- [Hosted CI for the first PR commit](https://github.com/PKgamerzop/openbook-exam/actions/runs/45040846843) passed frontend, PostgreSQL and Chrome, dependency review, and staging backup and restore jobs. The follow-up commit adds PDF and session-recovery checks.

- The remote Chrome rehearsal induced a failed save and retried it, then reloaded the exam while the API was stopped. The connection retry restored the acknowledged answer and flag after service restart, with the timer still active. Submission succeeded. The UI now offers retry after a PDF load failure or temporary session-check outage.
