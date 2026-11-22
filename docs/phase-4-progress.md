# Phase 4 progress

Phase 3 acceptance was confirmed against the merged PR and CI. Issues #21–31 and their Development Tracker tasks were closed.

## Review branches

- [Phase 4A UI and PDF reader](https://github.com/PKgamerzop/openbook-exam/pull/47) targets main.
- Phase 4B adds the attempt workspace, state persistence and Windows rehearsals on top of the UI branch.

## Acceptance checklist

- [x] Role-aware shell, deep links and browser history.
- [x] Authenticated continuous PDF.js rendering, page and zoom navigation, text layer, document find, outlines and thumbnail sidebar.
- [x] Responsive question and references workspace with resizable desktop columns, timer and mobile panel switching.
- [x] Migration 0004, saved answers, independent flags, one private scratchpad and optimistic revision checks.
- [x] Exam-scoped bookmarks, optional titles and pins, including explicitly pre-released references.
- [x] Published calculator and PDF export control policies.
- [x] Serialized save, timed submission, stable finalization receipt and restartable expiry processing.
- [x] Idempotent ten-question Windows rehearsals.
- [ ] Human review of screenshots and practical reader and workspace usability.

## Verification and browser screenshots

- Chrome captured [sign-in](phase-4-screenshots/01-login.png), [lecturer dashboard](phase-4-screenshots/02-lecturer-dashboard.png), [course and exams](phase-4-screenshots/03-course-and-exams.png), [mobile library](phase-4-screenshots/04-reference-library-mobile.png), and [student dashboard](phase-4-screenshots/05-student-dashboard.png).
- Review the [mobile workspace](phase-4-screenshots/06-workspace-mobile.png), [mobile reader](phase-4-screenshots/07-reader-mobile.png), and [desktop split workspace](phase-4-screenshots/08-workspace-desktop.png).
- Chrome verified upload, image-only preview, a simulated network failure and retry, refresh recovery of answers and flags, an exact unified-search jump, and in-document match highlighting.
- The Windows rehearsal command produced the same two exam IDs on consecutive runs after upgrading to migration 0004. Existing demo exams remained available.
- Verify practical usability in human review with a representative course corpus. The current browser evidence uses Chrome and synthetic documents.

## Implementation notes

Student APIs project stems and options without returning grading keys. The attempt row is locked before applying saves or finalizing. Revision conflicts require the student to reload server-saved work or retry after a transient failure. A failed voluntary save keeps submission blocked until the student retries or explicitly reloads acknowledged work. The expiry worker and API use the same finalized state. An attempt's response JSON becomes read-only at finalization.

PDF.js's rendering queue owns the visible page canvases and selectable text. Local find uses the PDF.js find controller. Unified search continues to query only the permitted full-text index. Thumbnail images are rendered near the current page at low resolution. The published export setting offers the browser's PDF print and download entry points. The controls do not prevent copying or screenshots.

Use the [Windows walkthrough](../README.md#exercise-phase-4) to rehearse deliberate submission, expiry and connection recovery. The real browser suite can save screenshots by setting OPENBOOK_SCREENSHOTS to a writable directory.
