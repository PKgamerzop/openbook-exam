# Phase 2 progress

Verified the Phase 1 merge at 8fa98c2 and checked existing GitHub issues #1–8. Started the core exam branch from origin/main. See [work packages](phase-2-plan.md).

## Verification for review

| Issue | Evidence |
| --- | --- |
| [#10](https://github.com/PKgamerzop/openbook-exam/issues/10) | PostgreSQL 17 applied 0001 → 0002 → 0001 → 0002 in isolated schemas. The development database reports 0002 at head. |
| [#11](https://github.com/PKgamerzop/openbook-exam/issues/11) | Chrome signed both roles in and out. API tests rejected invalid credentials, wrong roles, missing mutation headers and a revoked cookie. |
| [#12](https://github.com/PKgamerzop/openbook-exam/issues/12) | The browser created a course and enrolled a seeded student. API tests denied another lecturer access and rejected an ineligible assignment. |
| [#13](https://github.com/PKgamerzop/openbook-exam/issues/13) | Validation tests rejected missing stems, insufficient options, invalid keys and missing topics. Optional objectives and question ordering passed. |
| [#14](https://github.com/PKgamerzop/openbook-exam/issues/14) | The browser saved settings, displayed a validation error, previewed the key and published the saved draft. |
| [#15](https://github.com/PKgamerzop/openbook-exam/issues/15) | Two competing publishes accepted one revision. The old snapshot survived replacement. Saving and publishing at the effective opening returned 409. |
| [#16](https://github.com/PKgamerzop/openbook-exam/issues/16) | Four simultaneous starts returned one identical row and deadline. Upcoming, closed, expired and unassigned starts were rejected. Payload assertions checked the student field allowlist. |
| [#17](https://github.com/PKgamerzop/openbook-exam/issues/17) | Headless Chrome used the production React bundle, real FastAPI and PostgreSQL for the lecturer and student workflows. |
| [#18](https://github.com/PKgamerzop/openbook-exam/issues/18) | 11 backend tests including Chrome passed. Ruff lint and format passed. Seven Vitest tests, ESLint, TypeScript and the Vite production build passed. |
| [#19](https://github.com/PKgamerzop/openbook-exam/issues/19) | Setup, seeding, security, manual reproduction and migration recovery are documented. Human review is outstanding. |

The [Development Tracker](https://app.notion.com/p/41f6a9609e1181e5a389c2d4e0a41f69) links each work package to its issue. The [branch CI runs](https://github.com/PKgamerzop/openbook-exam/actions?query=branch%3Aphase-2%2Fcore-exams) report hosted results. The reviewer can reproduce the complete flow using the [Windows setup and checks](../README.md).

The pilot uses locally seeded accounts and text resource policies. Phase 3 adds permitted PDF versions. Phase 4 adds answer persistence and timed submission. Scoring and feedback follow in Phase 5.
