# Phase 6 security review

## Findings and changes

| Priority | Finding | Mitigation and verification |
| --- | --- | --- |
| High | A provider selected through development environment variables could make external calls if carried into deployment. | Staging and production omit assistance routes and UI. Startup rejects an enabled provider, a provider credential and insecure cookie mode. App services have no external network path in Compose. |
| High | Serving private routes without a defined TLS and origin policy risks exposing sessions and examination data. | Serve one HTTPS origin. Validate the host and browser mutation origin, require the existing custom mutation header, retain HttpOnly/SameSite=Strict/Secure cookies, and mark API responses no-store. |
| Medium | Unhandled SQL errors can interrupt workflows, and exception output may contain sensitive context. | Hide SQL parameters, return generic 503s for database errors, and emit payload-free operational events. Use independent liveness and readiness probes. |
| Medium | Worker loops need to remain observable during outage and recover from interruption. | Indexer and expiry catch database errors, log generic events and publish heartbeats on successful work. PDF claims recover through leases. Atomic PostgreSQL finalization continues to create grades. |

## Review coverage

Existing PostgreSQL tests exercise role and course ownership, assigned students, frozen exam revisions, scoped PDF metadata and byte ranges, suppressed answer keys, private feedback and release timing. The attempt state check and write share a row lock. The PDF parser runs with file, page, text, time and memory bounds. The search UI renders snippets as text. Browser export controls remain a user-interface setting. Viewers can still copy or capture information visible on their device.

Sessions rotate on login and are removed on logout. Session lifetime is eight hours from login. Stage operators should use fresh sign-ins before a timed rehearsal and confirm supported exam duration with the institution. The gateway replaces the client-IP header used by the per-process failed-login limiter. The worker cap remains two concurrent password checks. Rehearse real login arrival patterns and shared networks before the pilot. PostgreSQL is private to Compose. The bootstrap database role currently owns the installation and also runs the application. Review a dedicated runtime role and host-level access controls before deployment.

npm audit and pip-audit reported no known findings for the pinned application dependencies. The candidate uses digest-pinned PostgreSQL 17.12, Caddy 2.11.9 and Python 3.14.10 security releases. Review full image scan results and test public certificates and operational access on the chosen infrastructure. [PostgreSQL 17.12](https://www.postgresql.org/docs/release/17.12/) · [Caddy 2.11.9](https://github.com/caddyserver/caddy/releases/tag/v2.11.9) · [Python 3.14.10](https://www.python.org/downloads/release/python-31410/)
