# Phase 1 implementation plan

The [product specification](product-spec.md) defines the approved MCQ MVP. The [Notion roadmap](https://app.notion.com/p/41f6a9609e1181fda552db33039b0b9b) supplies milestone names. Earlier Notion descriptions of grading are historical proposals. Record results in [Phase 1 progress](phase-1-progress.md).

| Order | Issue and prerequisites | Acceptance and verification |
| --- | --- | --- |
| 1 | [#1](https://github.com/PKgamerzop/openbook-exam/issues/1) | Review scope, lifecycle, conventions, risks, links, and remaining decisions against the approved brief. |
| 2 | [#2](https://github.com/PKgamerzop/openbook-exam/issues/2), #1 | Run `npm.cmd ci`, `npm.cmd run build`, and open the welcome screen. Exercise connectivity in #8. |
| 3 | [#3](https://github.com/PKgamerzop/openbook-exam/issues/3), #1 | Start FastAPI from the README and verify the health contract with and without PostgreSQL in #8. |
| 4 | [#5](https://github.com/PKgamerzop/openbook-exam/issues/5), #1 | Run `docker compose config --quiet` and `docker compose up -d --wait db` with local placeholder settings. Verify the loopback binding. |
| 5 | [#4](https://github.com/PKgamerzop/openbook-exam/issues/4), #3 and the database from #5 | Run Alembic upgrade, head check, downgrade, and re-upgrade against a disposable database. Verify the health query. |
| 6 | [#6](https://github.com/PKgamerzop/openbook-exam/issues/6), #2–#5 | Run frontend lint, tests and build, backend Ruff and pytest, then record hosted CI results for the pull request. |
| 7 | [#7](https://github.com/PKgamerzop/openbook-exam/issues/7), #2, #4, #5 | Run the isolated synthetic PDF experiment. Verify extraction, a PostgreSQL keyword hit on the expected page, PDF.js navigation, multi-column behavior, and scanned view-only behavior. |
| 8 | [#8](https://github.com/PKgamerzop/openbook-exam/issues/8), #2–#6 | Repeat Windows setup from a clean checkout. Check UI, API, and database failure states, review the full diff, and record CI. |

Reuse the existing uncommitted skeleton. Keep the PDF experiment outside the frontend and backend application modules. Make one focused commit per issue on `phase-1/foundation`, update GitHub and Notion with evidence, and open one PR against `main`. Keep tasks in Review pending human review and merge.
