import { useRef, useState } from 'react'
import { api, useAction, useResource } from '../../app/api'

type Question = {
  position: number
  stem: string
  options: string[]
  correct: number
  selected: number | null
  outcome: string
  explanation?: string
}
type Feedback = {
  score: number
  maximum: number
  percentage: number
  correct: number
  incorrect: number
  unanswered: number
  questions: Question[]
}
type Result = { status: string; released: boolean; feedback?: Feedback }
type Group = { name: string; correct: number; total: number }
type Overview = {
  title: string
  version: number
  release: { released_at: string } | null
  release_block: string | null
  totals: {
    assigned: number
    started: number
    finalized: number
    graded: number
    submitted: number
    expired: number
    average: number | null
    highest: number | null
    lowest: number | null
  }
  students: {
    username: string
    attempt_id: number | null
    final_reason: string | null
    score: number | null
    maximum: number | null
  }[]
  distribution: { score: number; students: number }[]
  questions: {
    position: number
    stem: string
    correct: number
    incorrect: number
    unanswered: number
    total: number
  }[]
  topics: Group[]
  objectives: Group[]
}

function accuracy(n: number, total: number) {
  return total ? Math.round((100 * n) / total) + '%' : '—'
}

function FeedbackDetails({ data }: { data: Feedback }) {
  return (
    <>
      <p>
        <strong>
          {data.score}/{data.maximum} ({data.percentage}%)
        </strong>
      </p>
      <p>
        {data.correct} correct · {data.incorrect} incorrect · {data.unanswered}{' '}
        unanswered
      </p>
      <ol className="feedback-list">
        {data.questions.map((q) => (
          <li key={q.position}>
            <h4>{q.stem}</h4>
            <p>
              Your answer:{' '}
              {q.selected === null ? 'Unanswered' : q.options[q.selected]}
            </p>
            <p>Correct option: {q.options[q.correct]}</p>
            <p>Outcome: {q.outcome}</p>
            {q.explanation && <p>{q.explanation}</p>}
          </li>
        ))}
      </ol>
    </>
  )
}

export function StudentResult({ eid }: { eid: number }) {
  const [refresh, reload] = useState(0)
  const result = useResource<Result>(
    '/student/exams/' + eid + '/result',
    refresh,
  )
  return (
    <details className="exam-brief">
      <summary>My results</summary>
      <button onClick={() => reload((n) => n + 1)}>Refresh results</button>
      {result.error && <p role="alert">{result.error}</p>}
      {!result.data && !result.error && <p role="status">Loading results…</p>}
      {result.data &&
        (result.data.feedback ? (
          <FeedbackDetails data={result.data.feedback} />
        ) : (
          <p>
            {result.data.status === 'not_started'
              ? 'No attempt started.'
              : result.data.status === 'in_progress'
                ? 'Attempt in progress.'
                : `Attempt ${result.data.status}. Results await release.`}
          </p>
        ))}
    </details>
  )
}

function AttemptDetail({ root, id }: { root: string; id: number }) {
  const detail = useResource<Feedback>(root + '/attempts/' + id)
  if (detail.error) return <p role="alert">{detail.error}</p>
  return detail.data ? (
    <FeedbackDetails data={detail.data} />
  ) : (
    <p role="status">Loading grades…</p>
  )
}

function Breakdown({ title, groups }: { title: string; groups: Group[] }) {
  if (!groups.length) return null
  return (
    <div className="result-table">
      <table>
        <caption>{title}</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Correct</th>
            <th scope="col">Responses</th>
            <th scope="col">Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => (
            <tr key={g.name}>
              <th scope="row">{g.name}</th>
              <td>{g.correct}</td>
              <td>{g.total}</td>
              <td>{accuracy(g.correct, g.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function LecturerResults({
  eid,
  back,
}: {
  eid: number
  back: () => void
}) {
  const root = '/lecturer/exams/' + eid + '/results'
  const [refresh, reload] = useState(0)
  const [offset, paginate] = useState(0)
  const [attempt, select] = useState<{ id: number; name: string }>()
  const dialog = useRef<HTMLDialogElement>(null)
  const { run, error, busy } = useAction()
  const { data, error: failed } = useResource<Overview>(
    root + '?offset=' + offset,
    refresh,
  )
  return (
    <section className="results-dashboard">
      <button onClick={back}>Back to exam</button>
      <h2>{data?.title ?? 'Exam results'}</h2>
      {failed && <p role="alert">{failed}</p>}
      {!data && !failed && <p role="status">Loading exam results…</p>}
      {data && (
        <>
          <p>Published version {data.version}</p>
          <dl className="result-summary">
            {Object.entries(data.totals).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v === null ? '—' : Number(v.toFixed(2))}</dd>
              </div>
            ))}
            <div>
              <dt>Participation</dt>
              <dd>{accuracy(data.totals.started, data.totals.assigned)}</dd>
            </div>
            <div>
              <dt>Completion</dt>
              <dd>{accuracy(data.totals.finalized, data.totals.assigned)}</dd>
            </div>
          </dl>
          {data.release ? (
            <p>
              Released {new Date(data.release.released_at).toLocaleString()}
            </p>
          ) : (
            <>
              <button
                disabled={!!data.release_block}
                onClick={() => dialog.current?.showModal()}
              >
                Release results
              </button>
              {data.release_block && <p>{data.release_block}</p>}
            </>
          )}
          <button onClick={() => reload((n) => n + 1)}>Refresh results</button>
          {error && <p role="alert">{error}</p>}
          <dialog ref={dialog} aria-labelledby="release-heading">
            <h3 id="release-heading">
              Release results for version {data.version}?
            </h3>
            <p>
              Students with finalized attempts will see their own marks,
              answers, correct options and any authored explanations.
            </p>
            <button
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api(root + '/release', 'POST')
                  dialog.current?.close()
                  reload((n) => n + 1)
                })
              }
            >
              Confirm result release
            </button>
            <button onClick={() => dialog.current?.close()}>Cancel</button>
            {error && <p role="alert">{error}</p>}
          </dialog>
          <div className="result-table">
            <table>
              <caption>Assigned students</caption>
              <thead>
                <tr>
                  <th scope="col">Student</th>
                  <th scope="col">Attempt</th>
                  <th scope="col">Score</th>
                </tr>
              </thead>
              <tbody>
                {data.students.map((s) => (
                  <tr key={s.username}>
                    <th scope="row">
                      {s.score === null ? (
                        s.username
                      ) : (
                        <button
                          onClick={() =>
                            select({ id: s.attempt_id!, name: s.username })
                          }
                        >
                          {s.username}
                        </button>
                      )}
                    </th>
                    <td>
                      {s.final_reason ??
                        (s.attempt_id ? 'In progress' : 'Never started')}
                    </td>
                    <td>
                      {s.score === null
                        ? s.final_reason
                          ? 'Grade unavailable'
                          : '—'
                        : `${s.score}/${s.maximum}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {offset > 0 && (
            <button onClick={() => paginate(offset - 30)}>
              Previous students
            </button>
          )}
          {offset + 30 < data.totals.assigned && (
            <button onClick={() => paginate(offset + 30)}>Next students</button>
          )}
          {attempt && (
            <article>
              <h3>{attempt.name}</h3>
              <button onClick={() => select(undefined)}>
                Close attempt detail
              </button>
              <AttemptDetail root={root} id={attempt.id} />
            </article>
          )}
          <h3>Score distribution</h3>
          <p>
            Scores and accuracy use the {data.totals.graded} graded finalized
            attempts.
          </p>
          {data.distribution.length ? (
            <ul className="score-distribution">
              {data.distribution.map((d) => (
                <li key={d.score}>
                  <span>{d.score} points</span>
                  <meter
                    aria-label={d.score + ' points'}
                    min={0}
                    max={data.totals.graded}
                    value={d.students}
                  />
                  <span>{d.students} students</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>No finalized grades.</p>
          )}
          <div className="result-table">
            <table>
              <caption>Question accuracy</caption>
              <thead>
                <tr>
                  <th scope="col">Question</th>
                  <th scope="col">Correct</th>
                  <th scope="col">Incorrect</th>
                  <th scope="col">Unanswered</th>
                  <th scope="col">Accuracy</th>
                </tr>
              </thead>
              <tbody>
                {data.questions.map((q) => (
                  <tr key={q.position}>
                    <th scope="row">
                      {q.position + 1}. {q.stem}
                    </th>
                    <td>{q.correct}</td>
                    <td>{q.incorrect}</td>
                    <td>{q.unanswered}</td>
                    <td>{accuracy(q.correct, q.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            A question contributes to each of its topics and objectives, so
            totals can overlap.
          </p>
          <Breakdown title="Topic accuracy" groups={data.topics} />
          <Breakdown
            title="Learning-objective accuracy"
            groups={data.objectives}
          />
        </>
      )}
    </section>
  )
}
