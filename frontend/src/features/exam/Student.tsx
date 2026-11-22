import { useState } from 'react'
import { api, useAction, useResource } from '../../app/api'

type Details = {
  id: number
  title: string
  availability: string
  instructions: string
  rules: string
  duration: number
  calculator: boolean
  opens_at: string
  closes_at: string
}
type Attempt = {
  id: number
  deadline: string
  questions: { stem: string; options: string[] }[]
}

export function Student() {
  const [selected, select] = useState<number>()
  const [refresh, reload] = useState(0)
  const exams = useResource<Details[]>('/student/exams', refresh)
  if (selected)
    return (
      <ExamDetails
        id={selected}
        back={() => {
          select(undefined)
          reload((n) => n + 1)
        }}
      />
    )
  return (
    <section>
      <h2>Assigned examinations</h2>
      <button onClick={() => reload((n) => n + 1)}>Refresh exams</button>
      {exams.error ? (
        <p role="alert">{exams.error}</p>
      ) : !exams.data ? (
        <p>Loading examinations…</p>
      ) : (
        !exams.data.length && <p>No examinations assigned.</p>
      )}
      {exams.data?.map((e) => (
        <p key={e.id}>
          <button onClick={() => select(e.id)}>{e.title}</button>{' '}
          {e.availability}
        </p>
      ))}
    </section>
  )
}

function ExamDetails({ id, back }: { id: number; back: () => void }) {
  const path = '/student/exams/' + id
  const [refresh, reload] = useState(0)
  const { data, error: loadError } = useResource<Details>(path, refresh)
  const [attempt, setAttempt] = useState<Attempt>()
  const [index, setIndex] = useState(0)
  const { run, busy, error } = useAction()
  return (
    <section>
      <button onClick={back}>Assigned exams</button>
      {loadError ? (
        <p role="alert">{loadError}</p>
      ) : !data ? (
        <p>Loading examination…</p>
      ) : (
        <>
          <h2>{data.title}</h2>
          <p>
            {data.availability} · {data.duration} minutes
          </p>
          <p>
            {new Date(data.opens_at).toLocaleString()} –{' '}
            {new Date(data.closes_at).toLocaleString()}
          </p>
          <h3>Instructions</h3>
          <p>{data.instructions}</p>
          <h3>Permitted resources</h3>
          <p>{data.rules}</p>
          <p>Calculator {data.calculator ? 'permitted' : 'disabled'}</p>
          {attempt ? (
            <article>
              <p>
                Attempt {attempt.id} · Deadline{' '}
                {new Date(attempt.deadline).toLocaleString()}
              </p>
              <h3>
                Question {index + 1} of {attempt.questions.length}
              </h3>
              <p>{attempt.questions[index].stem}</p>
              <ol>
                {attempt.questions[index].options.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ol>
              <button disabled={!index} onClick={() => setIndex((i) => i - 1)}>
                Previous
              </button>
              <button
                disabled={index + 1 === attempt.questions.length}
                onClick={() => setIndex((i) => i + 1)}
              >
                Next
              </button>
            </article>
          ) : (
            <>
              <button
                disabled={busy || data.availability !== 'open'}
                onClick={() =>
                  void run(async () =>
                    setAttempt(await api<Attempt>(path + '/start', 'POST')),
                  )
                }
              >
                Start or resume attempt
              </button>
              <button onClick={() => reload((n) => n + 1)}>
                Refresh availability
              </button>
            </>
          )}
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
