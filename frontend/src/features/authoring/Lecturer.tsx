import { useState } from 'react'
import { navigate, useRoute } from '../../app/route'
import { api, useResource, useAction } from '../../app/api'
import { Icon } from '../../app/Icon'
import { Library } from '../references/Resources'
import { LecturerResults } from '../results/Results'
import { Editor } from './Editor'
import type { Course, Exam, Roster } from './model'

export function Lecturer() {
  const route =
    /^\/courses\/(\d+)(?:\/(references)|\/exams\/(\d+)(\/results)?)?$/.exec(
      useRoute(),
    )
  const cid = Number(route?.[1])
  const [name, setName] = useState('')
  const [refresh, reload] = useState(0)
  const list = useResource<Course[]>('/courses', refresh)
  const { run, busy, error } = useAction()
  if (cid && route?.[4]) {
    const examPath = '/courses/' + cid + '/exams/' + route[3]
    return (
      <LecturerResults
        key={route[3]}
        eid={Number(route[3])}
        back={() => navigate(examPath)}
      />
    )
  }
  if (cid)
    return (
      <CourseView
        key={cid}
        cid={cid}
        library={Boolean(route?.[2])}
        examId={Number(route?.[3])}
      />
    )
  return (
    <section className="lecturer-dashboard">
      <h1>Lecturer dashboard</h1>
      <div className="lecturer-grid">
        <div className="lecturer-card">
        <h3>Courses</h3>
        {list.error ||
          (!list.data
            ? 'Loading courses…'
            : !list.data.length && 'No courses yet.')}
        {list.data?.map((c) => (
          <button className="course-link button-secondary" key={c.id} onClick={() => navigate('/courses/' + c.id)}>
            <Icon name="book" /> <span>{c.name}</span><Icon name="right" />
          </button>
        ))}
        </div>
        <form className="lecturer-card"
          onSubmit={(e) => {
            e.preventDefault()
            void run(async () => {
              const c = await api<Course>('/courses', 'POST', { name })
              reload((n) => n + 1)
              navigate('/courses/' + c.id)
              setName('')
            })
          }}
        >
          <label>
            Course name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <button disabled={busy}><Icon name="plus" /> Create course</button>
        </form>
      </div>
      {error && <p role="alert">{error}</p>}
    </section>
  )
}

function CourseView({
  cid,
  library,
  examId,
}: {
  cid: number
  library: boolean
  examId: number
}) {
  const base = '/courses/' + cid
  const [refresh, reload] = useState(0)
  const examResource = useResource<Exam>(
    examId ? '/lecturer/exams/' + examId : '',
  )
  const exam = examId ? examResource.data : undefined
  const [username, setUsername] = useState('')
  const [title, setTitle] = useState('')
  const roster = useResource<Roster>('/courses/' + cid, refresh)
  const path = '/lecturer/courses/' + cid + '/exams'
  const exams = useResource<
    { id: number; title: string; published_number: number | null }[]
  >(path, refresh)
  const { run, busy, error } = useAction()
  if (exam && roster.data)
    return (
      <Editor
        key={exam.id}
        initial={exam}
        roster={roster.data}
        back={() => {
          navigate(base)
          reload((n) => n + 1)
        }}
      />
    )
  return (
    <section className="course-dashboard">
      <button className="button-quiet" onClick={() => navigate('/')}><Icon name="left" /> All courses</button>
      <h1>{roster.data?.name || 'Loading course…'}</h1>
      <nav aria-label="Course navigation">
        <button aria-pressed={!library} onClick={() => navigate(base)}>
          Exams and enrollment
        </button>
        <button
          aria-pressed={library}
          onClick={() => navigate(base + '/references')}
        >
          Reference Library
        </button>
      </nav>
      {library ? (
        <Library cid={cid} />
      ) : (
        <div className="lecturer-grid course-grid">
          <div className="lecturer-card enrollment-card">
            <h3>Enrollment</h3>
            <p>
              {roster.data?.students.map((s) => s.username).join(', ') ||
                'No enrolled students.'}
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                void run(async () => {
                  await api('/courses/' + cid + '/enroll', 'POST', { username })
                  setUsername('')
                  reload((n) => n + 1)
                })
              }}
            >
              <label>
                Student username
                <input
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </label>
              <button disabled={busy}>Enroll student</button>
            </form>
          </div>
          <div className="lecturer-card examinations-card">
            <h3>Examinations</h3>
            {!exams.data
              ? 'Loading exams…'
              : !exams.data.length && 'No examinations yet.'}
            {exams.data?.map((x) => (
              <div className="exam-row" key={x.id}>
                <button className="button-quiet" onClick={() => navigate(base + '/exams/' + x.id)}>
                  <Icon name="file" />
                  {x.title}
                </button>
                <span className="processing-status">{x.published_number ? 'Published' : 'Draft'}</span>
              </div>
            ))}
            <form
              onSubmit={(e) => {
                e.preventDefault()
                void run(async () => {
                  const created = await api<Exam>(path, 'POST', { title })
                  navigate(base + '/exams/' + created.id)
                  setTitle('')
                })
              }}
            >
              <label>
                New exam title
                <input
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <button disabled={busy}><Icon name="plus" /> Create draft</button>
            </form>
          </div>
        </div>
      )}
      {examId > 0 && examResource.error && (
        <p role="alert">{examResource.error}</p>
      )}
      {(error || roster.error || exams.error) && (
        <p role="alert">{error || roster.error || exams.error}</p>
      )}
    </section>
  )
}
