import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api, useAction, useResource } from '../../app/api'
import { Icon } from '../../app/Icon'
import { Sketchpad } from './Sketchpad'
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
  rules,
  result,
  back,
}: {
  path: string
  title: string
  references: boolean
  calculator: boolean
  rules: ReactNode
  result: ReactNode
  back: () => void
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
      rules={rules}
      result={result}
      back={back}
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
  rules,
  result,
  back,
  reload,
}: {
  initial: Attempt
  path: string
  title: string
  references: boolean
  calculator: boolean
  rules: ReactNode
  result: ReactNode
  back: () => void
  reload: () => void
}) {
  const endpoint = path + '/attempt'
  const [responses, setResponses] = useState(initial.responses)
  const [scratchpad, setScratchpad] = useState(initial.scratchpad)
  const [index, setIndex] = useState(0)
  const [panel, setPanel] = useState<'questions' | 'tools'>('questions')
  const [tool, setTool] = useState(references ? 'references' : 'notes')
  const [wideReference, setWideReference] = useState(false)
  const [filter, setFilter] = useState('all')
  const [scratchTool, setScratchTool] = useState<'text' | 'draw'>('text')
  const reviewDialog = useRef<HTMLDialogElement>(null)
  const questionPane = useRef<HTMLElement>(null)
  const [status, setStatus] = useState('Saved')
  const [receipt, setReceipt] = useState(initial.final_reason ? initial : null)
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
  const total = initial.questions.length
  function selectQuestion(next: number) {
    setIndex(next)
    questionPane.current?.scrollTo({ top: 0 })
  }
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
      <section className="workspace-receipt">
        <button className="button-quiet" onClick={back}><Icon name="left" />Assigned exams</button>
        <div className="receipt-icon"><Icon name={receipt.final_reason === 'expired' ? 'clock' : 'check'} /></div>
        <h2>{title}</h2>
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
        {result}
      </section>
    )

  return (
    <div className="exam-workspace" data-panel={panel}>
      <header className="workspace-header">
        <div className="workspace-title">
          <span className="workspace-label">Examination</span>
          <h1>{title}</h1>
        </div>
        <div className="workspace-meta">
          {rules}
          <span className="save-status" role="status" data-status={status === 'Saved' ? 'saved' : status.startsWith('Save failed') ? 'failed' : 'pending'}>
            <Icon name={status === 'Saved' ? 'check' : 'refresh'} />{status}
          </span>
          <span className="exam-timer" data-warning={remaining <= 300} role="timer">
            <Icon name="clock" />
            <span>{Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, '0')} <small>remaining</small></span>
          </span>
        </div>
      </header>
      {status.startsWith('Save failed') && (
        <div className="save-recovery">
          <button onClick={() => void flush()} disabled={disabled}>Retry saves</button>
          <button className="button-secondary" onClick={() => {
            if (window.confirm('Discard current unsaved edits and reload server-saved work?')) reload()
          }}>Reload saved work</button>
        </div>
      )}
      <nav className="workspace-mobile-tabs" aria-label="Workspace panels">
        <button aria-pressed={panel === 'questions'} onClick={() => setPanel('questions')}>
          <Icon name="grid" /> Questions
        </button>
        <button aria-pressed={panel === 'tools'} onClick={() => setPanel('tools')}>
          <Icon name={references ? 'book' : 'edit'} /> Exam tools
        </button>
      </nav>
      <div className="workspace-grid" data-wide-reference={wideReference && tool === 'references'}>
        <aside className="question-sidebar" aria-label="Question navigator">
          <details open>
            <summary><Icon name="grid" /> Question navigator</summary>
            <div className="navigator-content">
              <label className="question-filter">
                <span className="sr-only">Filter questions</span>
                <select value={filter} onChange={(e) => setFilter(e.target.value)}>
                  <option value="all">All questions</option>
                  <option value="unanswered">Unanswered</option>
                  <option value="flagged">Flagged</option>
                </select>
              </label>
              <div className="question-map">
                {initial.questions.map((_, i) => {
                  const saved = responses[i]
                  const isAnswered = saved?.answer != null
                  if ((filter === 'unanswered' && isAnswered) || (filter === 'flagged' && !saved?.flagged)) return null
                  return (
                    <button key={i} aria-current={i === index ? 'step' : undefined}
                      data-answered={isAnswered}
                      aria-label={`Question ${i + 1}, ${isAnswered ? 'answered' : 'unanswered'}${saved?.flagged ? ', flagged' : ''}`}
                      onClick={() => selectQuestion(i)}>
                      {i + 1}
                      {saved?.flagged && <Icon name="flag" className="map-flag" />}
                    </button>
                  )
                })}
              </div>
              {((filter === 'unanswered' && answered === total) || (filter === 'flagged' && !flagged))
                && <p className="muted">No {filter} questions.</p>}
              <div className="map-legend">
                <span><i className="answered-key" /> Answered</span>
                <span><i /> Unanswered</span>
                <span><Icon name="flag" /> Flagged</span>
              </div>
            </div>
          </details>
        </aside>

        <div className="question-panel">
          <article className="question-body" ref={questionPane}>
            {question && (
              <fieldset className="question-fieldset" disabled={disabled}>
                <legend>Question {index + 1} <span>of {total}</span></legend>
                <p className="question-stem">{question.stem}</p>
                <p className="answer-instruction">Select one answer</p>
                {question.options.map((option, i) => (
                  <label className="answer-option" key={i}>
                    <input type="radio" name="answer" checked={response.answer === i}
                      onChange={() => change({ answer: i })} />
                    <span className="option-letter" aria-hidden="true">{String.fromCharCode(65 + i)}</span>
                    <span>{option}</span>
                    <Icon name="check" className="option-check" />
                  </label>
                ))}
                <div className="question-actions">
                  <button className="button-quiet" disabled={response.answer === null}
                    onClick={() => change({ answer: null })}>Clear answer</button>
                  <button className="button-quiet" aria-pressed={response.flagged}
                    onClick={() => change({ flagged: !response.flagged })}>
                    <Icon name="flag" />{response.flagged ? 'Remove flag' : 'Flag question'}
                  </button>
                </div>
              </fieldset>
            )}
          </article>
          <footer className="question-footer">
            <div className="question-pagination">
              <button className="button-secondary" disabled={!index} onClick={() => selectQuestion(index - 1)}>
                <Icon name="left" /> Previous
              </button>
              <button disabled={index + 1 >= total} onClick={() => selectQuestion(index + 1)}>
                Next <Icon name="right" />
              </button>
            </div>
            <button className="button-quiet submit-trigger" disabled={disabled} onClick={() => reviewDialog.current?.showModal()}>
              <Icon name="check" /> Review and submit
            </button>
          </footer>
        </div>

        <aside className="workspace-tools" aria-label="Exam tools">
          <nav className="tool-tabs" aria-label="Exam tools">
            {references && <button aria-pressed={tool === 'references'} onClick={() => setTool('references')}>
              <Icon name="book" /> References
            </button>}
            {calculator && <button aria-pressed={tool === 'calculator'} onClick={() => setTool('calculator')}>
              <Icon name="calculator" /> Calculator
            </button>}
            <button aria-pressed={tool === 'notes'} onClick={() => setTool('notes')}>
              <Icon name="edit" /> Scratchpad
            </button>
            {tool === 'references' && <button className="reference-width icon-button"
              aria-label={wideReference ? 'Restore reference panel width' : 'Widen reference panel'}
              title={wideReference ? 'Restore reference panel width' : 'Widen reference panel'}
              onClick={() => setWideReference((current) => !current)}>
              <Icon name={wideReference ? 'shrink' : 'expand'} />
            </button>}
          </nav>
          {references && (
            <div className="tool-content reference-tool" hidden={tool !== 'references'}>
              <Resources path={path + '/references'} />
            </div>
          )}
          {calculator && (
            <div className="tool-content" hidden={tool !== 'calculator'}>
              <Calculator />
            </div>
          )}
          <div className="tool-content" hidden={tool !== 'notes'}>
            <h2>Scratchpad</h2>
            <nav className="scratch-tabs" aria-label="Scratchpad mode">
              <button aria-pressed={scratchTool === 'text'} onClick={() => setScratchTool('text')}>Notes</button>
              <button aria-pressed={scratchTool === 'draw'} onClick={() => setScratchTool('draw')}>Sketch</button>
            </nav>
            <div hidden={scratchTool !== 'text'}>
              <label>
                Exam notes
                <textarea maxLength={12000} value={scratchpad} disabled={disabled}
                  placeholder="Write calculations or notes here…"
                  onChange={(e) => {
                    setScratchpad(e.target.value)
                    enqueue('scratchpad', {
                      path: '/scratchpad',
                      data: { scratchpad: e.target.value },
                    })
                  }} />
              </label>
              <p className="muted scratch-hint">Notes save automatically and are available across questions.</p>
            </div>
            <div hidden={scratchTool !== 'draw'}><Sketchpad disabled={disabled} /></div>
          </div>
        </aside>
      </div>
      <footer className="workspace-progress">
        <progress value={answered} max={total || 1} aria-label="Questions answered" />
        <strong>{answered} / {total}</strong> answered
        <span><Icon name="flag" /> {flagged} flagged</span>
      </footer>
      <dialog ref={reviewDialog} className="workspace-review" aria-labelledby="review-title"
        onCancel={(e) => { if (submitting) e.preventDefault() }}>
          <div role="region" aria-label="Review before submission">
            <h2 id="review-title">Review before submission</h2>
            <p>{answered} answered · {total - answered} unanswered · {flagged} flagged</p>
            <div className="review-actions">
              <button className="button-secondary" disabled={submitting}
                onClick={() => reviewDialog.current?.close()}>Back to questions</button>
              <button disabled={disabled} onClick={() => void run(async () => {
                setSubmitting(true)
                try {
                  if (!(await flush()))
                    throw Error('Pending changes could not be confirmed. Retry saves or reload saved work before submitting.')
                  setReceipt(await api<Attempt>(endpoint + '/submit', 'POST', {
                    revision: revision.current,
                  }))
                } finally {
                  setSubmitting(false)
                }
              })}>Confirm submission</button>
            </div>
            {error && <p role="alert">{error}</p>}
          </div>
      </dialog>
    </div>
  )
}
