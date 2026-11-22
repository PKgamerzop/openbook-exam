# Phase 4 implementation plan

[Phase 3 PR #32](https://github.com/PKgamerzop/openbook-exam/pull/32) merged. [CI on its final revision](https://github.com/PKgamerzop/openbook-exam/actions/runs/45010022726) passed.

## Review sequence

Review the application shell and PDF reader first. Exercise the reader with real Chrome and authorized fixtures before integrating the timed attempt workspace. Stack persistence and workspace changes if the UI review is still open. Keep exam content and reference permissions anchored to the published revision.

## Work packages

| Package | Depends on | Acceptance |
| --- | --- | --- |
| P4-00 UI foundation | Phase 3 | Role-aware navigation, URL history, accessible forms and screenshots. |
| P4-01 PDF reader | 00 | Continuous scrolling, selectable text, local find, page and zoom controls, thumbnails and outline. |
| P4-02 Workspace | 00, 01, 03 | Responsive question and reference panels, timer and submission controls. |
| P4-03 Attempt schema | Phase 3 | Additive migration preserves existing attempts and version bindings. |
| P4-04 Autosave | 03 | Save, clear and recover answers with stale-write protection. |
| P4-05 Navigator and flags | 02, 04 | Direct navigation, independent flags and review counts. |
| P4-06 Scratchpad | 03, 04 | One private persisted note per attempt. |
| P4-07 Bookmarks and pins | 01, 03 | Validate exact permitted document versions and pages before and during exams. |
| P4-08 Calculator | 02 | Policy-gated scientific operations with safe parsing. |
| P4-09 Submission and expiry | 03, 04 | Row-locked durable finalization and idempotent receipts. |
| P4-10 Reconnection | 04, 09 | Visible pending changes and safe recovery from tab conflicts or network loss. |
| P4-11 Demo | 02–10 | Idempotent Windows rehearsal with ten MCQs and both calculator policies. |
| P4-12 Verification | 00–11 | PostgreSQL, Chrome, responsiveness, screenshots and hosted CI. |
| P4-13 Documentation | 00–12 | Windows walkthrough, review PRs and evidence. |

## Decisions

Use the official PDF.js viewer components for scroll-driven rendering, text layers, in-document find and internal PDF destinations. Keep React in charge of the toolbar and authenticated file URLs. Use the attempt row as the transaction boundary for answer saves and finalization. Grade and release feedback in Phase 5.
