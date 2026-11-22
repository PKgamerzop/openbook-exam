# Phase 6 performance report

The synthetic load driver uses independent authenticated sessions on two exams per wave. It checks distinct state, negative authorization responses, PDF ranges, acknowledged answers after fresh reads, submission replay and lecturer-confirmed scores. Authentication is prepared before the timed wave. Each student owns its HTTP cookie jar.

The fixture includes a 120-page original text PDF, two two-page original text PDFs and a one-page image-only PDF. Fixtures and thresholds are documented in the [pilot runbook](pilot-runbook.md). Percentiles describe end-to-end HTTPS API latency from the Windows host. They do not measure browser rendering or a real WAN.

## Measured results

Pending isolated staging load runs. A small loopback synthetic benchmark cannot establish public capacity.

## Initial connection-per-request run

Windows Docker Desktop allocated 12 logical processors and 7.6 GiB to Linux. The host processor was an Intel Core i5-12450HX. The initial stack used PostgreSQL 17.10 with its image defaults and SQLAlchemy's default pool settings. Two exams each used a different permitted reference set. Five rounds per learner covered answer saves, server refreshes, keyword searches and PDF ranges before submission and replay.

| Concurrent sessions | Elapsed | Measured req/s | Save p50 / p95 / p99 | Search p50 / p95 / p99 | PDF range p50 / p95 / p99 | HTTP errors |
| --- | --- | --- | --- | --- | --- | --- |
| 30 | 57.4 s | 13.6 | 2086 / 2190 / 2207 ms | 2087 / 2170 / 2179 ms | 2097 / 2193 / 2235 ms | 0 / 780 |
| 60 | 58.0 s | 26.9 | 2078 / 2150 / 2206 ms | 2108 / 2210 / 2236 ms | 2113 / 2250 / 2304 ms | 0 / 1,560 |

Both waves verified every acknowledged answer, expected access denials, distinct attempts, replayed finalization and lecturer-visible grades. Both missed the provisional targets of answer-save p95 below 1 second and search p95 below 2 seconds. This first driver opened a fresh HTTPS connection for each request and included Windows loopback connection setup. A point-in-time sample read 79 MiB for the API, 59 MiB for PostgreSQL, 18 MiB for the gateway, 49 MiB for the indexer and 42 MiB for the expiry process. This sample did not measure peak load or database lock wait.
