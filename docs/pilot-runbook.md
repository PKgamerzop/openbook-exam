# Pilot runbook

## Synthetic HTTPS staging

Follow [deployment](deployment.md) first. Generate a synthetic password in a local secret manager, then enter it through stdin. This fixture requires loopback HTTPS staging and an isolated database with no existing accounts. Repeat seeding keeps the same IDs and does not reset existing attempts or schedules.

~~~powershell
$pilotSecret = Read-Host 'Synthetic pilot password'
$pilotSecret | docker compose -p openbook-p6-stage --env-file .env.staging -f compose.production.yaml exec -T api python -m app.pilot --synthetic-staging |
  Set-Content -Encoding ascii .phase6-local/pilot.json
$pilotSecret | python scripts/phase6_load.py --ca .phase6-local/stage-root.crt --manifest .phase6-local/pilot.json --concurrency 30 --rounds 5 --password-stdin --output .phase6-local/load30.json
$pilotSecret | python scripts/phase6_load.py --ca .phase6-local/stage-root.crt --manifest .phase6-local/pilot.json --concurrency 60 --rounds 5 --password-stdin --output .phase6-local/load60.json
~~~

Sign in as pilot_lecturer or pilot_student_01 through pilot_student_60. The rehearsal exam is reserved for interactive checks. Historical released and unreleased exams include submitted and expired attempts and use production grading. Load waves consume separate reserved exams. Repeat measurements on a new isolated project to avoid modifying published schedules or clearing attempts.

## Supervised flow

Use one lecturer account to author and publish an exam with a scheduled opening, authorized cohort and reference set. A supervisor checks identity and attendance outside OpenBook. Learners sign in with independent browser sessions and confirm the correct exam. Ask each learner to find a permitted reference, flag a question, save a response and submit. The lecturer checks the completion list and grades. After exam close, release and verify private student feedback.

## Remote flow

Use a separate learner session. Confirm an acknowledged edit, simulate offline mode during the next edit, verify the pending/error state, reconnect and retry before the deadline. Reload or reopen and compare the acknowledged answers, flags and scratchpad. Rehearse deliberate submission and an overdue attempt with the expiry worker temporarily paused. Confirm that its restart processes overdue work and that the stored final reason and grade are stable.

## Institutional decisions

| Decision | State |
| --- | --- |
| Hosting owner and location | Blocked pending approval and infrastructure selection |
| Institution approval and authority to process student data | Blocked pending signed approval |
| Cohort size and maximum exam duration | Pending pilot capacity and long-session confirmation |
| Identity provisioning and local account or SSO policy | Pending institutional decision |
| Data retention, deletion and permitted PDF distribution | Pending institutional policy |
| Availability, recovery point and recovery time targets | Pending institutional policy |
| Remote vs supervised exams and support coverage | Pending institutional policy |
| Human usability approval | Pending review with lecturers and students |
