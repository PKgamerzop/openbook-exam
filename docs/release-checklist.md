# Release checklist

| Gate | Status |
| --- | --- |
| Merged Phase 5 technical baseline | Ready |
| Production image build and initial migrated staging startup | Ready |
| Trusted HTTPS, secure cookies and AI-disabled operation | Ready for loopback HTTPS staging |
| PostgreSQL and automated Chrome regression | Ready locally, hosted checks tracked in PR |
| Populated PostgreSQL migration and application dependency review | Ready on synthetic data, full image scan pending |
| Timed exam, simulated connectivity failure and worker restart | Ready for synthetic rehearsal |
| Representative PDF reader and search | Ready on synthetic documents, institutional corpus pending |
| 30 and 60 concurrent synthetic load | Ready for short loopback bursts |
| Coordinated backup and isolated restore | Ready on synthetic data |
| Human usability and supervised/remote institutional processes | Pending |
| Phase 6 exact-main CI after review and merge | Pending |
| Real student enrollment and public deployment | Blocked pending hosting and institutional approval |

Attach actual evidence from the [progress record](phase-6-progress.md) before updating status. The release owner must review candidate CI and migration impact before merging. Run the exact main CI afterward. Compare the [pilot decisions](pilot-runbook.md#institutional-decisions) with confirmed institutional policy.
