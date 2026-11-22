# Phase 6 performance report

The synthetic load driver uses independent authenticated sessions on two exams per wave. It checks distinct state, negative authorization responses, PDF ranges, acknowledged answers after fresh reads, submission replay and lecturer-confirmed scores. Authentication is prepared before the timed wave. Each student owns its HTTP cookie jar.

The fixture includes a 120-page original text PDF, two two-page original text PDFs and a one-page image-only PDF. Fixtures and thresholds are documented in the [pilot runbook](pilot-runbook.md). Percentiles describe end-to-end HTTPS API latency from the Windows host. They do not measure browser rendering or a real WAN.

## Initial connection-per-request run

Windows 11 Home (build 26300) with Docker Desktop allocated 12 logical processors and 7.6 GiB to Linux. The host processor was an Intel Core i5-12450HX. The initial stack used PostgreSQL 17.10 with its image defaults and SQLAlchemy's default pool settings. Two exams each used a different permitted reference set. Five rounds per learner covered answer saves, server refreshes, keyword searches and PDF ranges before submission and replay.

| Concurrent sessions | Elapsed | Measured req/s | Save p50 / p95 / p99 | Search p50 / p95 / p99 | PDF range p50 / p95 / p99 | HTTP errors |
| --- | --- | --- | --- | --- | --- | --- |
| 30 | 57.4 s | 13.6 | 2086 / 2190 / 2207 ms | 2087 / 2170 / 2179 ms | 2097 / 2193 / 2235 ms | 0 / 780 |
| 60 | 58.0 s | 26.9 | 2078 / 2150 / 2206 ms | 2108 / 2210 / 2236 ms | 2113 / 2250 / 2304 ms | 0 / 1,560 |

Both waves verified every acknowledged answer, expected access denials, distinct attempts, replayed finalization and lecturer-visible grades. Both missed the provisional targets of answer-save p95 below 1 second and search p95 below 2 seconds. This first driver opened a fresh HTTPS connection for each request and included Windows loopback connection setup. A point-in-time sample read 79 MiB for the API, 59 MiB for PostgreSQL, 18 MiB for the gateway, 49 MiB for the indexer and 42 MiB for the expiry process. This sample did not measure peak load or database lock wait.


## Persistent HTTPS connections

The second run used the same host and fixture with PostgreSQL 17.12 and one HTTP/TLS connection per learner. Authentication took place before the timed workload. The initial 60-student attempt-start burst stalled because requests waiting for a SQLAlchemy connection used the same AnyIO thread capacity needed by handlers returning connections. API logs recorded database failures after the pool’s 30-second timeout. Twenty attempts started without any saved responses. The change gives checkout its own capacity limiter and bounds individual pool waits to five seconds.

| Concurrent sessions | Elapsed | Measured req/s | Save p50 / p95 / p99 | Search p50 / p95 / p99 | PDF range p50 / p95 / p99 | HTTP errors |
| --- | --- | --- | --- | --- | --- | --- |
| 30 before checkout fix | 7.32 s | 106.6 | 256 / 395 / 530 ms | 278 / 396 / 494 ms | 342 / 511 / 577 ms | 0 / 780 |
| 60 after checkout fix | 12.52 s | 124.6 | 451 / 590 / 612 ms | 424 / 560 / 716 ms | 552 / 684 / 817 ms | 0 / 1,560 |

The 60-session retry reused the twenty empty, unsubmitted attempts without resetting them. All 60 students completed, with zero lost acknowledged answers, incorrect grades, duplicate finalizations or failures in the scripted isolation checks. After the fix, p95 was 776 ms for start and 623 ms for submission.

These are short burst tests with a small text corpus and no background indexing surge in the timed interval. Recommend at most 30 learners for an initial supervised cohort, subject to rehearsal on the actual host and network. The 60-student result tested additional headroom. A long-session soak, login burst and realistic institutional corpus are still needed before increasing capacity.


With the indexer stopped, staging queued an authenticated upload of the 120-page synthetic PDF. After restart it became searchable in 4.24 seconds including container startup and the status read. The drill measured recovery through the API. Peak parser memory and a 100-page real teaching corpus remain to be measured.
