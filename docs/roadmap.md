# Development roadmap

GitHub holds versioned requirements and technical decisions. GitHub issues track implementation and link to product requirement IDs. Notion holds milestones and review notes with links back to GitHub. Codex works in small reviewable changes with the checks described in [AGENTS.md](../AGENTS.md).

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| 1. Foundation and Environment | Reviewed scope, React and FastAPI skeleton, local PostgreSQL, CI, and an isolated synthetic PDF experiment. | Review the [execution plan](phase-1-plan.md), reproduce the Windows setup, and record CI and PDF findings. |
| 2. Core Examination System | MCQ authoring, scheduling, rules, assignments, topic tags, and frozen grading keys (L01, L02, L04, S01). | Verify authorization, schedule enforcement, and the opening-time freeze. Confirm the institutional sign-in approach. |
| 3. Reference Management | PDF upload, indexing, permitted reference selection, and page-level search (L02, L03, S03). | Verify access isolation, page mapping, and processing failures on representative files. |
| 4. Student Examination Workspace | Side-by-side workspace, bookmarks and pins, scratchpad, calculator, question status, and timed submission (S02, S04–S07). | Reproduce a timed attempt, recovery after refresh, and the expected result under concurrent saves and submission. |
| 5. AI Assistance and Evaluation | Automatic MCQ grading, feedback release, analytics, and optional lecturer AI assistance (L05–L07, S08). | Verify deterministic scores, release visibility, and manually reviewed AI suggestions. Approve the provider and data handling before enabling AI. |
| 6. Testing and Deployment | Supervised and remote rehearsals, load checks, and operational readiness. | Confirm hosting, cohort size, corpus, capacity limits, and recovery procedures before pilot enrollment. |

## Phase 1 checklist

1. Record lecturer and student requirements, acceptance criteria, and MVP boundaries.
2. Define the future directory structure, exam and attempt lifecycles, security boundaries, and failure behavior.
3. Tie requirement IDs and feasibility checks to the phase exit gates.
4. Propose root conventions for implementation, testing, security, and scope.
5. Verify the skeleton, CI, and PDF experiment, then return the foundation pull request for review.
