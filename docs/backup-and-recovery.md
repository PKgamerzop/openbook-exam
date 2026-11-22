# Backup and recovery

The backup helper pauses gateway, API and both workers. This makes the PostgreSQL dump and PDF archive consistent with each other. Schedule an approved maintenance window with no active examination, prohibit other writers and save the deployment commit and configuration references separately. Keep database credentials and CA private keys in the institution’s protected secret store.

~~~powershell
python scripts/phase6_backup.py backup .phase6-local/drill-01 --project openbook-p6-stage --env-file .env.staging
python scripts/phase6_backup.py restore .phase6-local/drill-01 --project openbook-p6-restore --env-file .phase6-local/restore.env
~~~

Prepare the restore environment from the staging example with its own generated password and unused HTTPS port. Set OPENBOOK_ORIGIN and OPENBOOK_HTTPS_PORT to the same port. Build its gateway before restore with the documented Compose build command. The target database and private PDF volume must be empty. The script verifies both artifact checksums, restores the transactional database dump and PDF archive, and starts the stack on the restored schema. Rehearse login and lecturer results on the target before exposing traffic. Compare allowed PDF bytes, grades and release records. Check pending leases, index state and overdue attempts as workers resume.

Record elapsed time and the last usable backup timestamp in a drill log. A possible starting policy is nightly encrypted off-host backups and a pre-migration checkpoint, with institutional sign-off on retention and acceptable data loss and outage duration. An example rotation is seven daily copies plus four weekly copies, subject to institutional retention and deletion policy. Restrict artifact access and the integrity manifest to operators. Treat archives as sensitive examination material. Test decryption and restoration on a schedule.

If migration fails, keep the gateway and writers stopped. Preserve logs with sensitive values excluded, inspect and correct the failure, then rerun the migration. Restore a known-good coordinated backup into a new project if schema/data compatibility is uncertain. Verify grades, releases, indexing and documents before cutover. Preserve the original project for investigation.

## Synthetic recovery evidence

The initial 17.10 staging snapshot took 17.0 seconds, including stopping and restarting its application services. Restoration into a fresh PostgreSQL 17.12 project took 27.2 seconds through worker readiness. Trusted HTTPS smoke checks then matched the 120-page private PDF's SHA-256, verified its authenticated range bytes, and confirmed the expected grades and release visibility. No production recovery point or time objective has been agreed. This drill used a small synthetic corpus.
