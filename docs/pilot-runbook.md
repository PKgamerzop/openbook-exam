# Pilot runbook

## Synthetic HTTPS staging

Follow [deployment](deployment.md) first. Generate a synthetic password in a local secret manager, then enter it through stdin. This fixture requires loopback HTTPS staging and an isolated database with no existing accounts. Repeat seeding keeps the same IDs and does not reset existing attempts or schedules.

~~~powershell
$securePilotSecret = Read-Host 'Synthetic pilot password' -AsSecureString
$pilotSecret = [System.Net.NetworkCredential]::new('', $securePilotSecret).Password
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

Start with a supervised cohort of at most 30 learners after an on-host rehearsal. Have a designated operator provision local accounts and ask learners to sign in shortly before the exam. Confirm identity policy and a maximum supported exam duration before enrolling a real cohort.

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


## Rehearsal evidence

The automated supervised Chrome flow authored, scheduled and published an exam, signed in as a learner, saved and submitted a response, and checked the lecturer-visible grade. Separate Chrome coverage verified release and mobile private feedback. Local staging used fictional accounts and a 120-page permitted reference. A human-supervised cohort and an off-site network still require institutional approval and infrastructure.

The remote Chrome rehearsal simulated a dropped answer-save request and stopped the staging API. A reload while it was down showed a service outage. After the API started, **Retry connection** recovered the same session, acknowledged answer, question flag and remaining timer. The learner then submitted successfully.
