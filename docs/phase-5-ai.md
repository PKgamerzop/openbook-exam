# Optional lecturer authoring assistance

Phase 5B branches independently from main. Results, release and grading run without this module. Follow the existing Windows setup in the README. Before starting the backend, set the provider in that PowerShell session.

```powershell
$env:OPENBOOK_AI_PROVIDER = 'mock'
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Sign in as the demo lecturer. Open an exam draft or an upcoming exam. Expand **Optional authoring assistance**. Ask for scenario ideas or choose a saved question and request review. Click **Apply proposed stem** after checking the original question and findings. You can then revise the local wording, save a draft, and publish separately using the existing workflow. The mock is deterministic and makes zero external requests. The default is `disabled`.

To enable live use, set `OPENBOOK_AI_PROVIDER=openai`, `OPENBOOK_AI_MODEL` to the approved structured-output model, and `OPENAI_API_KEY` through your local secret mechanism. Restart the API. The provider request contains only explicit scenario fields or the selected saved question's stem, options, key index, topics and objectives. Authored fields must contain course material only. Student records and PDFs are excluded from the payload. The request sets `store: false`. Apply your institution's approved provider and data handling requirements before enabling live mode.

The adapter uses the [Responses API structured output format](https://developers.openai.com/api/docs/guides/structured-outputs) and validates the result again locally. It allows four requests per minute per lecturer, a process-wide limit of 30 in that window and two concurrent requests. The request uses a 12-second socket timeout, bounded authoring fields and up to 1,600 output tokens. Limits are process-local. Production multi-worker budgets need centralized accounting. Logs record the exception class without tracing prompts or responses.

For a planning example, assume 2,500 input and 1,600 output tokens per request. At illustrative rates of USD 1 per million input tokens and USD 4 per million output tokens, 100 requests would cost approximately USD 0.89. Substitute current rates and actual usage for the approved model. Disabled and mock modes incur no provider charges.

## Reproduce the quality evaluation

Use the [synthetic question pairs](phase-5-ai-evaluation.csv). The revised items were manually written after applying the mock review rubric; they are illustrative candidates. In the UI, use the baseline stem and its options, run the mock, then compare the original, the proposed wording and the manually edited candidate. Record whether the provider contribution was adopted, adapted, or dismissed.

Ask two domain lecturers to review randomly labeled pairs independently using the rubric below. Score each criterion 0 for an unmet criterion, 1 for partial, and 2 for satisfied. Record item-level comments and resolve any factual or answer-key disagreement before adopting an item. Compare paired rubric results and document drawbacks and disagreements.

| Criterion | Check |
| --- | --- |
| Factual correctness | The proposed key follows from given facts and course references. |
| Clarity | The problem, decision and required output are explicit. |
| Ambiguity | The facts support exactly one defensible option. |
| Cognitive demand | The student applies a concept to a given case. |
| Authenticity | The setting and constraints plausibly occur in practice. |
| Distractor quality | Alternatives reflect plausible misconceptions. |
| Objective alignment | The decision exercises the stated learning objective. |

Initial inspection found that the deterministic mock repeated the same generic findings across questions. Its proposed prefix did not resolve the underlying ambiguity. The hand-written revisions add workload and decision constraints, but subject-matter reviewers still need to verify their keys and distractors. There are no independent rubric ratings or live-provider quality findings yet.

[Chrome screenshot of the mock review](phase-5-ai-screenshots/01-mock-authoring-review.png)
