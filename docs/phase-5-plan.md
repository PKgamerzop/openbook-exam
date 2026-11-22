# Phase 5 implementation plan

Phase 4 integration PR #49 is merged. Its hosted CI passed. Human review of Phase 4 screenshots and practical usability remains open.

## Review sequence

Phase 5A targets main with deterministic grading, release and analytics. Phase 5B branches independently from main for optional lecturer authoring assistance. Both can be reviewed and merged in either order. Provider calls are disabled by default.

| Package | Depends on | Acceptance |
| --- | --- | --- |
| [P5-00 — Prerequisites, planning and Phase 4 reconciliation](https://github.com/PKgamerzop/openbook-exam/issues/50) | Phase 4 | Verify merged CI and preserve pending usability review |
| [P5-01 — Grade schema and migration](https://github.com/PKgamerzop/openbook-exam/issues/51) | 00 | Upgrade old finalized attempts and constrain grade and release records |
| [P5-02 — Deterministic grading and finalization integration](https://github.com/PKgamerzop/openbook-exam/issues/52) | 01 | Grade the frozen revision atomically in every finalization path |
| [P5-03 — Lecturer results management](https://github.com/PKgamerzop/openbook-exam/issues/53) | 02 | Owner-scoped attempt listing and grading details |
| [P5-04 — Secure result release workflow](https://github.com/PKgamerzop/openbook-exam/issues/54) | 03 | Idempotent version-scoped release after close and complete grading |
| [P5-05 — Student results and feedback](https://github.com/PKgamerzop/openbook-exam/issues/55) | 04 | Private completion status and released assessment details |
| [P5-06 — Exam, question and topic analytics](https://github.com/PKgamerzop/openbook-exam/issues/56) | 02 | Finalized counts, distribution and labeled question/topic accuracy |
| [P5-07 — Optional AI provider infrastructure](https://github.com/PKgamerzop/openbook-exam/issues/57) | 00 | Disabled default, local mock, bounded validated OpenAI adapter |
| [P5-08 — AI scenario-design assistance](https://github.com/PKgamerzop/openbook-exam/issues/58) | 07 | Suggestions use explicitly supplied authoring fields |
| [P5-09 — AI question-quality review and lecturer approval](https://github.com/PKgamerzop/openbook-exam/issues/59) | 07 | Selected MCQ review and explicit draft edits |
| [P5-10 — Lecturer UI and usability improvements](https://github.com/PKgamerzop/openbook-exam/issues/60) | 03–09 | Responsive results and authoring panels with browser evidence |
| [P5-11 — Reproducible demonstration results](https://github.com/PKgamerzop/openbook-exam/issues/61) | 02–06 | Idempotent synthetic grades and release examples |
| [P5-12 — Security tests, regression tests and AI evaluation](https://github.com/PKgamerzop/openbook-exam/issues/62) | 01–11 | PostgreSQL, Chrome and reproducible human evaluation rubric |
| [P5-13 — Documentation, CI and final review](https://github.com/PKgamerzop/openbook-exam/issues/63) | 00–12 | Reviewable PRs, Windows walkthrough and hosted results |


Use an immutable SQL scoring function in migration 0005. A database trigger grades attempts in the same transaction as the existing finalization and keeps all existing API and worker paths consistent. Backfill uses the same function. Release is version-scoped and requires a closed exam and complete grades for every started attempt.
