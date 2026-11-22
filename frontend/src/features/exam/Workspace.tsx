import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { api, useAction, useResource } from '../../app/api'
import { Calculator } from './Calculator'
import { Resources } from '../references/Resources'

type Response = { answer: number | null; flagged: boolean }
type Attempt = {
  id: number
  deadline: string
  server_time: string
  revision: number
  responses: Record<string, Response>
  scratchpad: string
  final_reason: 'submitted' | 'expired' | null
  finalized_at: string | null
  questions: { stem: string; options: string[] }[]
}
type Edit = { path: string; data: Response | { scratchpad: string } }

export function AttemptWorkspace({
  path,
  title,
  references,
  calculator,
}: {
  path: string
  title: string
  references: boolean
  calculator: boolean
}) {
  const [generation, reload] = useState(0)
  const attempt = useResource<Attempt>(path + '/attempt', generation)
  if (attempt.error) return <p role="alert">{attempt.error}</p>
  if (!attempt.data) return <p role="status">Loading saved attempt…</p>
  return (
    <Workspace
      key={generation}
      initial={attempt.data}
      path={path}
      title={title}
      references={references}
      calculator={calculator}
      reload={() => reload((n) => n + 1)}
    />
  )
}

function Workspace({
  initial,
  path,
  title,
  references,
  calculator,
  reload,
}: {
  initial: Attempt
  path: string
  title: string
  references: boolean
  calculator: boolean
  reload: () => void
}) {
  const endpoint = path + '/attempt'
  const [responses, setResponses] = useState(initial.responses)
  const [scratchpad, setScratchpad] = useState(initial.scratchpad)
  const [index, setIndex] = useState(0)
  const [panel, setPanel] = useState('questions')
  const [referenceWidth, resize] = useState(58)
  const [status, setStatus] = useState('Saved')
  const [receipt, setReceipt] = useState(initial.final_reason ? initial : null)
  const [review, setReview] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const { run, error } = useAction()
  const revision = useRef(initial.revision)
  const edits = useRef(new Map<string, Edit>())
  const saving = useRef<Promise<boolean> | null>(null)
  const debounce = useRef<number | undefined>(undefined)
  const localStart = useRef(performance.now())
  const budget = Date.parse(initial.deadline) - Date.parse(initial.server_time)
  const [remaining, setRemaining] = useState(
    Math.max(0, Math.ceil(budget / 1000)),
  )
  useEffect(() => {
    if (receipt) return
    const interval = window.setInterval(() => {
      setRemaining(
        Math.max(
          0,
          Math.ceil((budget - (performance.now() - localStart.current)) / 1000),
        ),
      )
    }, 250)
    return () => window.clearInterval(interval)
  }, [budget, receipt])
  useEffect(() => {
    if (remaining || receipt) return
    let cancelled = false
    const refresh = () =>
      void api<Attempt>(endpoint)
        .then((state) => {
          if (!cancelled && state.final_reason) setReceipt(state)
        })
        .catch(() => {
          if (!cancelled) setStatus('Awaiting server confirmation')
        })
    refresh()
    const timer = window.setInterval(refresh, 3000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [remaining, receipt, endpoint])
  useEffect(() => () => window.clearTimeout(debounce.current), [])

  function flush(): Promise<boolean> {
    if (saving.current) return saving.current
    const save = async () => {
      while (edits.current.size) {
        const [key, edit] = edits.current.entries().next().value!
        setStatus('Saving')
        try {
          const result = await api<Attempt>(endpoint + edit.path, 'PUT', {
            ...edit.data,
            revision: revision.current,
          })
          revision.current = result.revision
          if (edits.current.get(key) === edit) edits.current.delete(key)
        } catch (failure) {
          setStatus(
            failure instanceof Error
              ? 'Save failed. ' + failure.message
              : 'Save failed',
          )
          return false
        }
      }
      setStatus('Saved')
      return true
    }
    saving.current = save().finally(() => {
      saving.current = null
    })
    return saving.current
  }

  function enqueue(key: string, edit: Edit) {
    edits.current.set(key, edit)
    setStatus('Saving')
    window.clearTimeout(debounce.current)
    debounce.current = window.setTimeout(() => void flush(), 250)
  }

  const question = initial.questions[index]
  const response = responses[index] ?? { answer: null, flagged: false }
  const disabled = !remaining || submitting
  const answered = Object.values(responses).filter(
    (r) => r.answer !== null,
  ).length
  const flagged = Object.values(responses).filter((r) => r.flagged).length
  function change(patch: Partial<Response>) {
    const data = { ...response, ...patch }
    setResponses({ ...responses, [index]: data })
    enqueue(String(index), { path: '/questions/' + index, data })
  }

  if (receipt)
    return (
      <article className="workspace-receipt">
        <h3>
          {receipt.final_reason === 'expired'
            ? 'Time expired'
            : 'Exam submitted'}
        </h3>
        <p>
          Attempt {receipt.id} ·{' '}
          {new Date(receipt.finalized_at!).toLocaleString()}
        </p>
        <p>
          {
            Object.values(receipt.responses).filter((r) => r.answer !== null)
              .length
          }{' '}
          answers recorded.
        </p>
      </article>
    )

  return (
    <div className="exam-workspace">
      <header className="workspace-header">
        <strong>{title}</strong>
        <span
          className={remaining <= 300 ? 'deadline-warning' : ''}
          role="timer"
        >
          {Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, '0')}{' '}
          remaining
        </span>
        <span role="status">{status}</span>
      </header>
      {status.startsWith('Save failed') && (
        <div>
          <button onClick={() => void flush()} disabled={disabled}>
            Retry saves
          </button>
          <button
            onClick={() => {
              if (
                window.confirm(
                  'Discard current unsaved edits and reload server-saved work?',
                )
              )
                reload()
            }}
          >
            Reload saved work
          </button>
        </div>
      )}
      <nav className="workspace-tabs" aria-label="Workspace panels">
        <button
          aria-pressed={panel === 'questions'}
          onClick={() => setPanel('questions')}
        >
          Questions
        </button>
        {references && (
          <button
            aria-pressed={panel === 'references'}
            onClick={() => setPanel('references')}
          >
            References
          </button>
        )}
      </nav>
      {references && (
        <label className="workspace-resize">
          Reference panel width{' '}
          <input
            type="range"
            min={42}
            max={66}
            value={referenceWidth}
            onChange={(e) => resize(Number(e.target.value))}
          />
        </label>
      )}
      <div
        className={
          references
            ? 'workspace-grid workspace-with-references'
            : 'workspace-grid'
        }
        style={{ '--reference-width': referenceWidth + '%' } as CSSProperties}
      >
        <div
          className={
            'question-panel ' + (panel === 'questions' ? 'panel-active' : '')
          }
        >
          <details open>
            <summary>Question navigator</summary>
            <div className="question-map">
              {initial.questions.map((_, i) => {
                const saved = responses[i]
                const answered = saved?.answer != null
                return (
                  <button
                    key={i}
                    aria-current={i === index ? 'step' : undefined}
                    data-answered={answered}
                    aria-label={`Question ${i + 1}, ${answered ? 'answered' : 'unanswered'}${saved?.flagged ? ', flagged' : ''}`}
                    onClick={() => setIndex(i)}
                  >
                    {i + 1}
                    {saved?.flagged ? ' ⚑' : ''}
                  </button>
                )
              })}
            </div>
          </details>
          <fieldset disabled={disabled}>
            <legend>
              Question {index + 1} of {initial.questions.length}
            </legend>
            <p>{question.stem}</p>
            {question.options.map((option, i) => (
              <label className="answer-option" key={i}>
                <input
                  type="radio"
                  name="answer"
                  checked={response.answer === i}
                  onChange={() => change({ answer: i })}
                />{' '}
                {option}
              </label>
            ))}
            <button
              onClick={() => change({ answer: null })}
              disabled={response.answer === null}
            >
              Clear answer
            </button>
            <button
              aria-pressed={response.flagged}
              onClick={() => change({ flagged: !response.flagged })}
            >
              {response.flagged ? 'Remove flag' : 'Flag question'}
            </button>
          </fieldset>
          <button disabled={!index} onClick={() => setIndex(index - 1)}>
            Previous
          </button>
          <button
            disabled={index + 1 >= initial.questions.length}
            onClick={() => setIndex(index + 1)}
          >
            Next
          </button>
          {calculator && <Calculator />}
          <details>
            <summary>Scratchpad</summary>
            <label>
              Exam notes
              <textarea
                maxLength={12000}
                value={scratchpad}
                disabled={disabled}
                onChange={(e) => {
                  setScratchpad(e.target.value)
                  enqueue('scratchpad', {
                    path: '/scratchpad',
                    data: { scratchpad: e.target.value },
                  })
                }}
              />
            </label>
          </details>
          <button disabled={disabled} onClick={() => setReview(true)}>
            Review and submit
          </button>
          {review && (
            <div
              className="workspace-review"
              role="region"
              aria-label="Review before submission"
            >
              <p>
                {answered} answered · {initial.questions.length - answered}{' '}
                unanswered · {flagged} flagged
              </p>
              <button
                disabled={disabled}
                onClick={() =>
                  void run(async () => {
                    setSubmitting(true)
                    try {
                      if (!(await flush()))
                        throw Error(
                          'Pending changes could not be confirmed. Retry saves or reload saved work before submitting.',
                        )
                      setReceipt(
                        await api<Attempt>(endpoint + '/submit', 'POST', {
                          revision: revision.current,
                        }),
                      )
                    } finally {
                      setSubmitting(false)
                    }
                  })
                }
              >
                Confirm submission
              </button>
              <button disabled={submitting} onClick={() => setReview(false)}>
                Back to questions
              </button>
              {error && <p role="alert">{error}</p>}
            </div>
          )}
        </div>
        {references && (
          <div
            className={
              'workspace-references ' +
              (panel === 'references' ? 'panel-active' : '')
            }
          >
            <Resources path={path + '/references'} />
          </div>
        )}
      </div>
    </div>
  )
}
