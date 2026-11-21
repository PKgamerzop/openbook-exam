# Project conventions

Start with the [product spec](docs/product-spec.md), [architecture](docs/architecture.md), and [project links](docs/project-links.md). Use the linked Notion roadmap and GitHub milestones to identify the current implementation phase.

## Changes and review

- Work only in the authorized [PKgamerzop/openbook-exam repository](https://github.com/PKgamerzop/openbook-exam). Use GitHub issues to identify engineering tasks and link changes to the relevant issue, phase, and product requirement IDs.
- Create a feature branch for each change and target `main` with a pull request. Never push directly to `main`.
- Test the change and review the diff before creating or updating a pull request. Mark tasks and milestones complete only after verifying their acceptance criteria and recording the evidence.
- Use React with TypeScript, FastAPI, PostgreSQL, and PDF.js. Keep code organized by feature within the modular monolith. Reuse existing logic where it fits and add dependencies or abstractions for a concrete need.
- Keep database schema changes in reviewed migrations. For changes to existing data, document compatibility, recovery, and any backfill. Keep API validation and authorization in the backend.
- Keep versioned requirements and architecture in the repository. Record important architecture decisions and milestone summaries in the [Notion Project HQ](docs/project-links.md), with links to the corresponding GitHub issues or pull requests.

## Verification

- Run the relevant [repository checks](README.md#checks) before handing off a change and report any checks that could not run.
- Use synthetic fixtures. Exercise backend authorization and state transitions through API integration tests, with PostgreSQL for search, migration, and transaction behavior. Verify affected browser workflows for exam delivery and feedback release.
- Cover relevant regressions for exam deadlines, overlapping saves and submission, duplicate submissions, and cross-exam PDF and search isolation. Check feedback visibility both before and after release when touching results.

## Security and scope

- Authorize each protected resource server-side, including PDF range requests and search. Keep original PDFs private. Validate untrusted uploads and bound processing by size, time, and resources.
- Never store API tokens or real credentials in repository files. Keep local secrets in the environment or an ignored local configuration file and use placeholders in examples. Exclude student answers, scratchpad text, credentials, and answer keys from logs. Limit AI assistance to lecturer requests using authored content and keep student data out of provider requests. Require human review and an explicit lecturer action to apply generated text.
- Keep the MVP focused on MCQs and authorized open-book references. AI grading, webcam proctoring, semantic search, descriptive grading, and full offline operation are out of scope. Defer PDF highlighting until search and bookmarks are stable.
