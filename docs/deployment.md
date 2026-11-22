# Deployment

Use one institution-controlled Linux host with Docker Engine and Compose. Caddy serves the frontend and proxies /api on the same origin. PostgreSQL, the API and the workers are reachable only inside Compose. Keep a durable disk for PostgreSQL and private PDFs and a separate encrypted backup destination. Build and deploy from the reviewed release commit. Size the pilot from measured evidence in the [performance report](performance-report.md).

## Windows loopback staging

From the repository root in PowerShell, generate an independent configuration and start a dedicated project. The .env.staging file and .phase6-local directory are ignored by Git.

~~~powershell
Copy-Item .env.production.example .env.staging
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$password = [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
(Get-Content -Raw .env.staging).Replace('replace-with-generated-password', $password) |
  Set-Content -Encoding ascii .env.staging
docker compose -p openbook-p6-stage --env-file .env.staging -f compose.production.yaml build api gateway
docker compose -p openbook-p6-stage --env-file .env.staging -f compose.production.yaml up -d --no-build --wait
New-Item -ItemType Directory -Force .phase6-local
docker compose -p openbook-p6-stage --env-file .env.staging -f compose.production.yaml cp gateway:/data/caddy/pki/authorities/local/root.crt .phase6-local/stage-root.crt
curl.exe --ssl-no-revoke --cacert .phase6-local/stage-root.crt https://localhost:8443/api/health
~~~

Generate the environment file once per fresh deployment. PostgreSQL applies its initial password when it creates the data volume. Trust the exported public CA only in the local test browser profile if needed. Open https://localhost:8443 after trust is configured. The [pilot runbook](pilot-runbook.md) shows how to add fictional accounts. Use the existing [Windows development instructions](../README.md#windows-setup) for the non-container development flow.

## Host setup after institutional approval

Create a separate protected .env.production outside the checkout and use its absolute path with --env-file. Set OPENBOOK_ENV=production, OPENBOOK_ORIGIN=https://the-approved-host, OPENBOOK_BIND to the approved public interface, OPENBOOK_HTTPS_PORT=443 and OPENBOOK_TLS_DIRECTIVE to an empty value for Caddy-managed public TLS. Arrange approved DNS and reachability on TCP 443 for TLS-ALPN validation. Keep 5432 and 8000 unpublished. Confirm the certificate, firewall, disk permissions, backups and restore rehearsal before provisioning real accounts.

Use the same build and up commands as staging with a distinct project name and environment path. PostgreSQL becomes healthy before the one-shot migration. API and workers start after the migration succeeds. The gateway follows API readiness. API liveness is /api/live and database readiness is /api/health. The worker health probe checks progress after completed database operations. Docker reports an unhealthy state without automatically restarting an unhealthy container that still runs.

## Operations

- Inspect Compose ps -a and logs for the relevant service. Workers log startup, completed batches or indexing outcome and database unavailability. Request diagnostics record response status and elapsed time. Disable proxy access logs for private API paths.
- If readiness fails, confirm DB service and disk availability. Pause examination admission when write availability is uncertain. After recovery, verify that API readiness and worker heartbeats return.
- If a worker is stalled, inspect its health and database lock activity, then restart the affected worker. A claimed PDF job is eligible again after its 90-second lease expires. Expiry processes overdue attempts in bounded batches.
- If disk is full, stop new uploads or admission and free approved space without deleting original PDFs or database files. Check failed jobs and verify backups before resuming.
- Record each backup and restore drill duration, backup timestamp, verification outcome and the operator in the institution’s operations log. See [backup and recovery](backup-and-recovery.md).
