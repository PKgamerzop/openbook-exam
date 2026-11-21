# Product specification

The Computer-Based Open-Book Examination Platform supports supervised and remote MCQ examinations. Lecturers manage exams and release results. Students complete assigned exams with access to the references and tools permitted for that exam.

## Lecturer requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| L01 | Author and schedule exams | A lecturer can create a draft, add MCQs with one correct option per question, and publish an exam with opening and closing times. An exam cannot open with missing required settings or invalid questions. |
| L02 | Configure rules and access | A lecturer can write student-facing rules, select permitted references, enable or disable the scientific calculator, and assign access to students. Students see the rules before starting. The published rules, questions, grading key, and reference selection are fixed from opening time. |
| L03 | Manage references | A lecturer can upload PDFs, name and organize them in a reference list, and select them for exams. Each upload displays a processing, searchable, view-only, or failed state. A failed indexing job can be retried. |
| L04 | Classify questions | A question requires at least one topic tag and accepts optional learning objectives. The author sees a validation error when saving a question without a topic tag. |
| L05 | Request optional AI assistance | A lecturer can request scenario suggestions and a question-quality review. Suggestions and reviews are visible only to authorized lecturers. Applying a suggestion requires an explicit author action, and publication follows the normal lecturer workflow. Authoring remains available when AI is disabled or unavailable. |
| L06 | Review grades and feedback | A lecturer can review automatic MCQ grades and student-facing feedback, then explicitly release results for students to view. |
| L07 | Review performance | A lecturer can see the number of finalized attempts, average score, and per-question and per-topic correctness. Reports identify the attempt population and show an empty state when no attempts are finalized. |

## Student requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| S01 | Access assigned exams | Students can see their assigned exams and start one attempt during the scheduled window. Opening an unassigned exam directly fails. |
| S02 | Read questions and references together | The attempt workspace displays questions and a PDF viewer together on desktop. Students can switch among permitted PDFs without leaving the attempt or losing their currently selected answer. |
| S03 | Search references by keyword | A query searches the searchable PDFs permitted for the exam. Each hit identifies its document and page and opens that page in the viewer. View-only PDFs can still be opened and read. |
| S04 | Bookmark and pin pages | Students can bookmark pages for later lookup and pin pages for quick access during the exam. Both lists persist across refresh and support removal. |
| S05 | Use exam tools | Students have one persistent scratchpad across all questions. A scientific calculator is available when the lecturer enables it, with basic arithmetic, powers, roots, logarithms, and trigonometric functions. |
| S06 | Track question status | The question navigator distinguishes answered and unanswered questions and displays a flag independently of answer status. Saved answers and flags survive a refresh. |
| S07 | Save answers and submit | The workspace reports when answers are saved or a save fails. Refresh restores the latest server-saved state. A timely submission finalizes once, and the exam deadline finalizes any existing open attempt using its eligible saved answers. |
| S08 | View released feedback | After release, a student can view their own score and student-facing feedback. Before release, the student sees submission status only. |

## MVP boundaries and assumptions

- The MVP serves one institution with lecturer-managed access assignments and one attempt per assigned student per exam. Supervised and remote exams share the same application workflow. Supervision procedures are managed outside the application.
- Each correct MCQ earns one point. Incorrect and unanswered questions earn zero. Topic reports count questions under each of their assigned tags, so topic groups may overlap.
- Student feedback means feedback released to students about their performance. An always-connected workflow is assumed. On connection loss, students can see that a save failed and retry while the exam is open.
- AI answer grading, webcam proctoring, semantic search, descriptive grading, and full offline support are outside the MVP. PDF text highlighting is deferred until keyword search and bookmarks are stable. Scanned or otherwise textless PDFs are view-only in the MVP.
- Institutional sign-in, hosting, pilot cohort size, and AI provider selection are gated in the [roadmap](roadmap.md). See the [architecture](architecture.md) for how timing, file access, and grading are enforced.
