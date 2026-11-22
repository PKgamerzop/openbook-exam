# Phase 3 reference management

Requirements L02, L03, S02 and S03. Extend the Phase 2 publication transaction and use the existing same-origin identity and role checks. PostgreSQL owns revision permissions, leases and page indexes. Private disk holds immutable PDF bytes.

| Work package | Depends on | Acceptance |
| --- | --- | --- |
| P3-01 Reference database schema and private file storage | Phase 2 | Apply and reverse additive migration 0003 with existing exams intact. Enforce version and page uniqueness and private opaque storage. |
| P3-02 Authorized PDF upload and validation | 01 | Stream a bounded upload for an owned course, validate PDF content and page count, reject invalid files and retain existing versions. |
| P3-03 Background text extraction and indexing | 01, 02 | Claim and recover jobs with leases, bound extraction, publish all pages atomically and distinguish searchable, view-only and failed PDFs. |
| P3-04 Lecturer reference library and organization | 02, 03 | Filter an owned course library by title, folder and topic, preview versions and retry failed jobs. |
| P3-05 Examination reference permissions and immutable versions | 01, 02 | Validate selected versions against the course and publish bindings under the existing exam lock. Default to active-attempt access. |
| P3-06 Authenticated PDF.js viewer and byte-range delivery | 04, 05 | Authorize complete and partial reads. Render, switch and navigate PDFs with one-based pages and cleanup. |
| P3-07 Unified page-level keyword search | 03, 05 | Rank permitted page hits with indexed PostgreSQL search, bounded inputs and plain-text snippets. |
| P3-08 Lecturer/student reference UI integration | 04–07 | Connect the library and draft selector to the course and exam views. Open a search hit on its page. |
| P3-09 Reproducible engineering demonstration data | 02, 03, 05 | Seed original DBMS PDFs, two scheduled exams and six students idempotently in approved local development databases. |
| P3-10 Security, regression, integration, and browser tests | 06–09 | Verify release windows, retry, range and search isolation, frozen versions, seed reruns and Chrome page rendering. |
| P3-11 Documentation and final Phase 3 verification | 01–10 | Record Windows setup, backup and recovery, demo walkthrough, check results, hosted CI and review PR. |
