import { useState } from 'react'
import { api, useResource, useAction } from '../../app/api'
import { Editor } from './Editor'
import type { Course, Exam, Roster } from './model'

export function Lecturer() {
  const [cid, select] = useState<number>()
  const [name, setName] = useState('')
  const [refresh, reload] = useState(0)
  const list = useResource<Course[]>('/courses', refresh)
  const { run, busy, error } = useAction()
  if (cid) return <CourseView cid={cid} back={() => select(undefined)} />
  return (
    <section>
      <h2>Lecturer dashboard</h2>
      <h3>Courses</h3>
      {list.error ||
        (!list.data
          ? 'Loading courses…'
          : !list.data.length && 'No courses yet.')}
      {list.data?.map((c) => (
        <p key={c.id}>
          <button onClick={() => select(c.id)}>{c.name}</button>
        </p>
      ))}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void run(async () => {
            const c = await api<Course>('/courses', 'POST', { name })
            reload((n) => n + 1)
            select(c.id)
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
        <button disabled={busy}>Create course</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </section>
  )
}

function CourseView({ cid, back }: { cid: number; back: () => void }) {
  const [refresh, reload] = useState(0)
  const [exam, setExam] = useState<Exam>()
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
          setExam(undefined)
          reload((n) => n + 1)
        }}
      />
    )
  return (
    <section>
      <button onClick={back}>All courses</button>
      <h2>{roster.data?.name || 'Loading course…'}</h2>
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
      <h3>Examinations</h3>
      {!exams.data
        ? 'Loading exams…'
        : !exams.data.length && 'No examinations yet.'}
      {exams.data?.map((x) => (
        <p key={x.id}>
          <button
            onClick={() =>
              void run(async () =>
                setExam(await api<Exam>('/lecturer/exams/' + x.id)),
              )
            }
          >
            {x.title}
          </button>{' '}
          {x.published_number ? 'Published' : 'Draft'}
        </p>
      ))}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void run(async () => {
            setExam(await api<Exam>(path, 'POST', { title }))
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
        <button disabled={busy}>Create draft</button>
      </form>
      {(error || roster.error || exams.error) && (
        <p role="alert">{error || roster.error || exams.error}</p>
      )}
    </section>
  )
}
