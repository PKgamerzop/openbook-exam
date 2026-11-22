# Phase 3 progress

[Phase 2 PR #20](https://github.com/PKgamerzop/openbook-exam/pull/20) merged at 2d166a0. [Hosted CI](https://github.com/PKgamerzop/openbook-exam/actions/runs/44981272259) passed. The user accepted Phase 2. Issues #10–19 are closed and the corresponding tracker tasks are Done. The [Phase 2 evidence](phase-2-progress.md) remains available.

[Phase 3 PR #32](https://github.com/PKgamerzop/openbook-exam/pull/32) targets main. [Hosted CI](https://github.com/PKgamerzop/openbook-exam/actions/runs/44984609386) passed for the implementation. The final migration regression upgraded a populated 0002 schema, read its original exam and resumed the same attempt. The local Windows seed ran twice with identical identifiers. PostgreSQL EXPLAIN confirmed a bitmap index scan on reference_search with sequential scans disabled for the small fixture corpus.

| Work package | Files | Verification |
| --- | --- | --- |
| [#21](https://github.com/PKgamerzop/openbook-exam/issues/21) | 0003_references.py, pdf_files.py | Migration 0003 ran on the local PostgreSQL database. The isolated PostgreSQL suite exercises downgrade and re-upgrade. Original files have UUID names outside the frontend. |
| [#22](https://github.com/PKgamerzop/openbook-exam/issues/22) | references.py, pdf_files.py | API tests accepted a lecturer upload and denied another lecturer and a student. Invalid content, size and page limits returned validation errors. A traversal-shaped display filename stayed metadata. |
| [#23](https://github.com/PKgamerzop/openbook-exam/issues/23) | reference_worker.py | The worker produced one-based searchable pages and a view-only raster. The integration test recovered an expired lease, forced a parse failure, retried and checked the resulting search index. |
| [#24](https://github.com/PKgamerzop/openbook-exam/issues/24) | Resources.tsx, Lecturer.tsx | Headless Chrome opened the course library, uploaded a PDF and rendered its preview. The course API scopes listings, organization and retry actions to the owner. |
| [#25](https://github.com/PKgamerzop/openbook-exam/issues/25) | authoring.py, attempts.py, Editor.tsx | The freeze test rejected changes after opening, preserved the prior version bytes, and republished an upcoming exam with new bindings. Phase 2 lifecycle tests passed. |
| [#26](https://github.com/PKgamerzop/openbook-exam/issues/26) | Viewer.tsx, references.py | A real Chrome canvas rendered page 2 and navigated back to page 1. API tests verified 206, Content-Range, suffix denial across exams and 416 for an unsatisfiable range. |
| [#27](https://github.com/PKgamerzop/openbook-exam/issues/27) | references.py, test_references.py | PostgreSQL returned the seven canonical terms on their expected pages. One query matched two permitted PDFs. Other-exam, view-only and absent hits were excluded. |
| [#28](https://github.com/PKgamerzop/openbook-exam/issues/28) | Student.tsx, Editor.tsx, Resources.tsx | The real browser suite covered lecturer upload and preview, attempt start, student keyword search and result navigation through the production React build. |
| [#29](https://github.com/PKgamerzop/openbook-exam/issues/29) | demo.py, demo_fixtures.py, Initialize-Demo.ps1 | The Windows seed command generated five indexed references and two published exams. The rerun test preserved IDs and an existing attempt. Credentials are Windows-user encrypted. |
| [#30](https://github.com/PKgamerzop/openbook-exam/issues/30) | test_browser.py, test_references.py | Fifteen backend tests passed locally with PostgreSQL and Chrome, including the Phase 2 lifecycle and both full browser workflows. Seven frontend tests passed. |
| [#31](https://github.com/PKgamerzop/openbook-exam/issues/31) | README.md, architecture.md, phase-3-plan.md | README, architecture and progress record document Windows startup, credentials, recovery, backup and the demonstration walkthrough. |

The [Windows walkthrough](../README.md#exercise-phase-3) covers both release policies. The synthetic corpus verifies behavior at small scale. Representative institutional files, extraction latency under concurrent uploads, storage capacity and pilot load remain operational validation work.
