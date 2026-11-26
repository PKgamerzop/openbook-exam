import { useState } from 'react'
import { navigate, useRoute } from '../../app/route'
import { api, useAction, useResource } from '../../app/api'
import { Icon } from '../../app/Icon'

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
    <section className="student-dashboard">
      <header className="dashboard-heading">
        <div>
          <span className="workspace-label">Student portal</span>
          <h1>Assigned examinations</h1>
        </div>
        <button className="button-secondary" onClick={() => reload((n) => n + 1)}>
          <Icon name="refresh" /> Refresh exams
        </button>
      </header>
      {exams.error ? (
        <p role="alert">{exams.error}</p>
      ) : !exams.data ? (
        <p>Loading examinations…</p>
      ) : (
        !exams.data.length && <p>No examinations assigned.</p>
      )}
      <div className="exam-catalog">
        {exams.data?.map((e) => (
          <article className="exam-card" key={e.id}>
            <div className="exam-card-top">
              <span className="feature-icon"><Icon name="file" /></span>
              <span className="processing-status" data-status={e.availability}>{e.availability}</span>
            </div>
            <h2><button className="exam-card-link" onClick={() => navigate('/exams/' + e.id)}>{e.title}</button></h2>
            <p><Icon name="clock" /> {e.duration} minutes</p>
          </article>
        ))}
      </div>
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
  if (data && (attempt || savedAttempt.data))
    return (
      <AttemptWorkspace path={path} title={data.title}
        references={data.pre_release !== undefined} calculator={data.calculator}
        rules={<ExamRules exam={data} compact />}
        result={<StudentResult eid={id} />}
        back={back} />
    )
  return (
    <section className="exam-details">
      <button className="button-quiet" onClick={back}><Icon name="left" /> Assigned exams</button>
      {loadError ? (
        <p role="alert">{loadError}</p>
      ) : !data ? (
        <p>Loading examination…</p>
      ) : (
        <>
          <h1>{data.title}</h1>
          <StudentResult eid={id} />
          <ExamRules exam={data} />
          {data.pre_release && data.availability === 'upcoming' && (
            <Resources path={path + '/references'} />
          )}
          <div className="exam-detail-actions">
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
            <button className="button-secondary" onClick={() => reload((n) => n + 1)}>
              <Icon name="refresh" />
              Refresh availability
            </button>
          </div>
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}

function ExamRules({ exam, compact = false }: { exam: Details; compact?: boolean }) {
  return (
    <details open={!compact} className={compact ? 'exam-brief exam-brief-compact' : 'exam-brief'}>
      <summary>{compact ? 'Exam rules' : 'Exam instructions and rules'}</summary>
      <div>
        <p>{exam.availability} · {exam.duration} minutes</p>
        <p>{new Date(exam.opens_at).toLocaleString()} – {new Date(exam.closes_at).toLocaleString()}</p>
        <h3>Instructions</h3>
        <p>{exam.instructions}</p>
        <h3>Permitted resources</h3>
        <p>{exam.rules}</p>
        <p>Calculator {exam.calculator ? 'permitted' : 'disabled'}</p>
        {exam.pre_release !== undefined && (
          <p>{exam.pre_release ? 'Released before opening. ' : ''}During the exam, references require an active attempt.</p>
        )}
      </div>
    </details>
  )
}
