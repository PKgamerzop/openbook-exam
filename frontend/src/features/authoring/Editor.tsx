import { useState } from 'react'
import { api, useAction, useResource } from '../../app/api'
import {
  localTime,
  moveQuestion,
  type Draft,
  type Exam,
  type Question,
  type Roster,
} from './model'

import { libraryPath, type Reference } from '../references/Resources'

function Preview({ draft }: { draft: Draft }) {
  return (
    <article>
      <h3>{draft.title}</h3>
      <p>{draft.instructions}</p>
      <p>{draft.rules}</p>
      <p>
        {draft.opens_at && new Date(draft.opens_at).toLocaleString()} –{' '}
        {draft.closes_at && new Date(draft.closes_at).toLocaleString()} ·{' '}
        {draft.duration} minutes
      </p>
      <p>
        Calculator {draft.calculator ? 'permitted' : 'disabled'} ·{' '}
        {draft.students.length} assigned
      </p>
      {draft.questions.map((q, i) => (
        <div key={i}>
          <strong>
            {i + 1}. {q.stem}
          </strong>
          <ol>
            {q.options.map((o, j) => (
              <li key={j}>
                {o}
                {j === q.correct ? ' (correct)' : ''}
              </li>
            ))}
          </ol>
        </div>
      ))}
    </article>
  )
}

export function Editor({
  initial,
  roster,
  back,
}: {
  initial: Exam
  roster: Roster
  back: () => void
}) {
  const [exam, setExam] = useState(initial)
  const [draft, setDraft] = useState(initial.draft)
  const [notice, setNotice] = useState('')
  const { busy, error, run } = useAction()
  const refs = useResource<Reference[]>(libraryPath(roster.id))
  const selected = draft.reference_versions ?? []
  const dirty = JSON.stringify(draft) !== JSON.stringify(exam.draft)
  function change(patch: Partial<Draft>) {
    setDraft({ ...draft, ...patch })
    setNotice('')
  }
  function question(index: number, patch: Partial<Question>) {
    change({
      questions: draft.questions.map((q, i) =>
        i === index ? { ...q, ...patch } : q,
      ),
    })
  }
  const path = '/lecturer/exams/' + exam.id
  async function persist(publish: boolean) {
    const updated = publish
      ? await api<Exam>(path + '/publish', 'POST', {
          edit_number: exam.edit_number,
        })
      : await api<Exam>(path, 'PUT', { edit_number: exam.edit_number, draft })
    setExam({ ...updated, published: publish ? updated.draft : exam.published })
    setDraft(updated.draft)
    setNotice(
      publish
        ? 'Published revision ' + updated.published_number
        : 'Draft saved',
    )
  }
  return (
    <section>
      <button
        onClick={() => {
          if (!dirty || window.confirm('Discard unsaved edits?')) back()
        }}
      >
        Back to course
      </button>
      <h2>{draft.title}</h2>
      <p>
        {exam.published_number
          ? 'Published revision ' + exam.published_number
          : 'Unpublished draft'}
        {dirty && ' · Unsaved changes'}
      </p>
      {exam.published && (
        <details>
          <summary>View published exam</summary>
          <Preview draft={exam.published} />
        </details>
      )}
      <fieldset disabled={busy || exam.frozen}>
        <legend>Exam settings</legend>
        <label>
          Exam title
          <input
            value={draft.title}
            onChange={(e) => change({ title: e.target.value })}
          />
        </label>
        <fieldset><legend>Permitted PDF versions</legend>
          {refs.error && <p role="alert">{refs.error}</p>}
          {!refs.data && !refs.error && <p>Loading references…</p>}
          {refs.data?.length === 0 && <p>No PDFs in this course library.</p>}
          {refs.data?.map(d=><label key={d.id}><input type="checkbox" checked={selected.includes(d.id)}
            onChange={e=>change({reference_versions:e.target.checked?[...selected,d.id]:selected.filter(v=>v!==d.id)})}/>
            {d.title} · v{d.number} · {d.status}</label>)}
          <label><input type="checkbox" checked={draft.pre_release ?? false} onChange={e=>change({pre_release:e.target.checked})}/> Release references to assigned students before opening</label>
          <p>During the examination, students need an active attempt.</p>
        </fieldset>
        <label>
          Instructions
          <textarea
            value={draft.instructions}
            onChange={(e) => change({ instructions: e.target.value })}
          />
        </label>
        <label>
          Permitted resources and rules
          <textarea
            value={draft.rules}
            onChange={(e) => change({ rules: e.target.value })}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.calculator}
            onChange={(e) => change({ calculator: e.target.checked })}
          />{' '}
          Permit calculator
        </label>
        {(['opens_at', 'closes_at'] as const).map((key, i) => (
          <label key={key}>
            {i ? 'Closes' : 'Opens'} (local time)
            <input
              type="datetime-local"
              value={localTime(draft[key])}
              onChange={(e) =>
                change({
                  [key]: e.target.value
                    ? new Date(e.target.value).toISOString()
                    : null,
                })
              }
            />
          </label>
        ))}
        <label>
          Duration in minutes
          <input
            type="number"
            min="1"
            value={draft.duration ?? ''}
            onChange={(e) =>
              change({ duration: Number(e.target.value) || null })
            }
          />
        </label>
        <fieldset>
          <legend>Assigned students</legend>
          {!roster.students.length && (
            <p>Enroll a student in the course first.</p>
          )}
          {roster.students.map((s) => (
            <label key={s.id}>
              <input
                type="checkbox"
                checked={draft.students.includes(s.id)}
                onChange={(e) =>
                  change({
                    students: e.target.checked
                      ? [...draft.students, s.id]
                      : draft.students.filter((id) => id !== s.id),
                  })
                }
              />{' '}
              {s.username}
            </label>
          ))}
        </fieldset>
        {draft.questions.map((q, i) => (
          <fieldset key={i}>
            <legend>Question {i + 1} · 1 point</legend>
            <label>
              Question stem
              <textarea
                value={q.stem}
                onChange={(e) => question(i, { stem: e.target.value })}
              />
            </label>
            {q.options.map((option, j) => (
              <div key={j}>
                <label>
                  Option {j + 1}
                  <input
                    value={option}
                    onChange={(e) =>
                      question(i, {
                        options: q.options.map((v, k) =>
                          k === j ? e.target.value : v,
                        ),
                      })
                    }
                  />
                </label>
                <label>
                  <input
                    type="radio"
                    name={'key' + i}
                    checked={q.correct === j}
                    onChange={() => question(i, { correct: j })}
                  />{' '}
                  Correct option {j + 1}
                </label>
                <button
                  disabled={q.options.length <= 2}
                  onClick={() =>
                    question(i, {
                      options: q.options.filter((_, k) => k !== j),
                      correct:
                        q.correct === j
                          ? -1
                          : q.correct - Number(q.correct > j),
                    })
                  }
                >
                  Remove option {j + 1}
                </button>
              </div>
            ))}
            <button
              onClick={() => question(i, { options: [...q.options, ''] })}
            >
              Add option
            </button>
            {(['topics', 'objectives'] as const).map((key) => (
              <label key={key}>
                {key === 'topics'
                  ? 'Topics (required, comma-separated)'
                  : 'Learning objectives (optional, comma-separated)'}
                <input
                  list={key}
                  value={q[key].join(',')}
                  onChange={(e) =>
                    question(i, {
                      [key]: e.target.value ? e.target.value.split(',') : [],
                    })
                  }
                />
              </label>
            ))}
            <button
              disabled={!i}
              onClick={() =>
                change({ questions: moveQuestion(draft.questions, i, -1) })
              }
            >
              Move up
            </button>
            <button
              disabled={i === draft.questions.length - 1}
              onClick={() =>
                change({ questions: moveQuestion(draft.questions, i, 1) })
              }
            >
              Move down
            </button>
            <button
              onClick={() =>
                change({ questions: draft.questions.filter((_, j) => j !== i) })
              }
            >
              Remove question
            </button>
          </fieldset>
        ))}
        {(['topics', 'objectives'] as const).map((key) => (
          <datalist id={key} key={key}>
            {roster.labels
              .filter(
                (l) => l.kind === (key === 'topics' ? 'topic' : 'objective'),
              )
              .map((l) => (
                <option key={l.name} value={l.name} />
              ))}
          </datalist>
        ))}
        <button
          onClick={() =>
            change({
              questions: [
                ...draft.questions,
                {
                  stem: '',
                  options: ['', ''],
                  correct: -1,
                  topics: [],
                  objectives: [],
                },
              ],
            })
          }
        >
          Add question
        </button>
        <button
          disabled={!dirty}
          onClick={() => void run(() => persist(false))}
        >
          Save draft
        </button>
        <button disabled={dirty} onClick={() => void run(() => persist(true))}>
          Validate and publish
        </button>
      </fieldset>
      <details>
        <summary>Preview draft</summary>
        <Preview draft={draft} />
      </details>
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
