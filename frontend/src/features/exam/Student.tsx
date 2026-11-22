import { useState } from 'react'
import { navigate, useRoute } from '../../app/route'
import { api, useAction, useResource } from '../../app/api'

import { StudentResult } from '../results/Results'
import { AttemptWorkspace } from './Workspace'
import { Resources } from '../references/Resources'

type Details = {
  pre_release?: boolean
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

export function Student() {
  const selected = Number(/^\/exams\/(\d+)$/.exec(useRoute())?.[1])
  const [refresh, reload] = useState(0)
  const exams = useResource<Details[]>('/student/exams', refresh)
  if (selected)
    return (
      <ExamDetails
        key={selected}
        id={selected}
        back={() => {
          navigate('/')
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
        <p className="exam-row" key={e.id}>
          <button onClick={() => navigate('/exams/' + e.id)}>{e.title}</button>{' '}
          <span className="processing-status" data-status={e.availability}>
            {e.availability}
          </span>
        </p>
      ))}
    </section>
  )
}

function ExamDetails({ id, back }: { id: number; back: () => void }) {
  const path = '/student/exams/' + id
  const [refresh, reload] = useState(0)
  const { data, error: loadError } = useResource<Details>(path, refresh)
  const [attempt, setAttempt] = useState(false)
  const savedAttempt = useResource<{ id: number }>(path + '/attempt')
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
          <StudentResult eid={id} />
          <details
            open={!(attempt || savedAttempt.data)}
            className="exam-brief"
          >
            <summary>Exam instructions and rules</summary>
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
            {data.pre_release !== undefined && (
              <p>
                {data.pre_release ? 'Released before opening. ' : ''}During the
                exam, references require an active attempt.
              </p>
            )}
          </details>
          {data.pre_release && data.availability === 'upcoming' && (
            <Resources path={path + '/references'} />
          )}
          {attempt || savedAttempt.data ? (
            <AttemptWorkspace
              path={path}
              title={data.title}
              references={data.pre_release !== undefined}
              calculator={data.calculator}
            />
          ) : (
            <>
              <button
                disabled={busy || data.availability !== 'open'}
                onClick={() =>
                  void run(async () => {
                    await api(path + '/start', 'POST')
                    setAttempt(true)
                  })
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
