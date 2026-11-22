# Phase 2 implementation plan

Foundation PR #9 is present on main at 8fa98c2. The Phase 1 tree matches the merged tree. No code prerequisite remains. Pilot sign-in uses development-seeded local accounts. Requirements L01, L02, L04 and S01 drive this milestone.

| Package | Work | Depends on | Acceptance |
| --- | --- | --- | --- |
| P2-01 | Core schema and migrations | Phase 1 | Upgrade 0001 on PostgreSQL, check foreign keys and uniqueness, roll back and reapply in an isolated database. |
| P2-02 | Local authentication and role enforcement | 01 | Seed hashed passwords, establish and revoke an expiring HttpOnly session, and reject unauthorized roles. |
| P2-03 | Courses and enrollment | 01, 02 | Lecturers select owned courses and enroll existing students. Assignment validates course eligibility. |
| P2-04 | MCQ authoring and classification | 01, 03 | Ordered MCQs require a stem, multiple options, one key and reusable topics. Objectives are optional. |
| P2-05 | Drafts, scheduling and policies | 02, 03, 04 | Owned drafts support rules, duration, opening and closing, assignments, editing and preview. |
| P2-06 | Publication and immutable revisions | 04, 05 | Validate publication, allow replacement before opening and serialize changes against the effective opening. |
| P2-07 | Assigned exams and attempt start | 02, 06 | Only assigned students discover exams. One idempotent attempt starts within the server window and never exposes the key. |
| P2-08 | Lecturer and student workflows | 03–07 | Exercise login, editing, validation, publication, discovery and first question through the browser. |
| P2-09 | Integration and lifecycle verification | 01–08 | Verify authorization, validation, boundary time, immutable versions, simultaneous starts, migrations and student payloads. |
| P2-10 | Documentation and review | 01–09 | Record verification, local reproduction, outstanding gates and link the review PR and project tracker. |

Use a single review branch. Keep immutable, complete revision snapshots and serialize publication and starts on the exam row. Review timing with a controllable clock and simultaneous PostgreSQL transactions. Exercise both roles in a browser before handoff.
