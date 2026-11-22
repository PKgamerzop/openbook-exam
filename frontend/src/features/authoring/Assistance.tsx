import { useState } from 'react'
import { api, useAction, useResource } from '../../app/api'
import type { Question } from './model'
import './assistance.css'

type Suggestion = {
  focus: string
  observation: string
  suggestion: string
  assumption: string
  proposed_stem: string
}
type Generated = {
  provider: 'mock' | 'openai'
  suggestions: Suggestion[]
  edit_number?: number
}

export function Assistance({
  eid,
  questions,
  edit,
  dirty,
  apply,
}: {
  eid: number
  questions: Question[]
  edit: number
  dirty: boolean
  apply: (index: number, stem: string) => void
}) {
  const root = '/lecturer/exams/' + eid + '/assistance'
  const status = useResource<{ provider: string }>(root)
  const [position, select] = useState(0)
  const [output, show] = useState<Generated>()
  const [review, setReview] = useState<{
    position: number
    original: Question
  }>()
  const [dismissed, dismiss] = useState<number[]>([])
  const { run, busy, error } = useAction()
  const provider = status.data?.provider
  const enabled = provider === 'mock' || provider === 'openai'
  function reset() {
    show(undefined)
    dismiss([])
    setReview(undefined)
  }
  return (
    <details className="authoring-assistance">
      <summary>Optional authoring assistance</summary>
      {status.error && <p role="alert">{status.error}</p>}
      {!status.data && !status.error && (
        <p role="status">Checking assistance…</p>
      )}
      {provider === 'mock' && (
        <p>Local mock · deterministic sample suggestions</p>
      )}
      {provider === 'openai' && (
        <p>
          OpenAI · requests send the form fields or selected saved question. Use
          course authoring material only.
        </p>
      )}
      {provider === 'disabled' && (
        <p>
          Assistance is disabled. You can continue writing questions manually.
        </p>
      )}
      {provider === 'unavailable' && (
        <p>
          Assistance is unavailable. You can continue writing questions
          manually.
        </p>
      )}
      {enabled && (
        <>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const fields = Object.fromEntries(new FormData(e.currentTarget))
              reset()
              void run(async () =>
                show(await api<Generated>(root + '/scenario', 'POST', fields)),
              )
            }}
          >
            <fieldset disabled={busy}>
              <legend>Scenario ideas</legend>
              <label>
                Topic
                <input name="topic" required maxLength={160} />
              </label>
              <label>
                Learning objective
                <input name="objective" maxLength={240} />
              </label>
              <label>
                Difficulty
                <select name="difficulty">
                  <option>Intermediate</option>
                  <option>Foundational</option>
                  <option>Advanced</option>
                </select>
              </label>
              <label>
                Engineering context
                <textarea name="context" maxLength={600} />
              </label>
              <label>
                Target skill
                <input name="skill" maxLength={240} />
              </label>
              <label>
                Additional authoring guidance
                <textarea name="prompt" maxLength={500} />
              </label>
              <button>Suggest scenarios</button>
            </fieldset>
          </form>
          <fieldset disabled={busy || dirty || !questions.length}>
            <legend>Review a saved question</legend>
            <label>
              Question
              <select
                value={position}
                onChange={(e) => select(Number(e.target.value))}
              >
                {questions.map((q, i) => (
                  <option key={i} value={i}>
                    {i + 1}. {q.stem}
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={() => {
                const original = questions[position]
                if (!original) return
                reset()
                void run(async () => {
                  const response = await api<Generated>(
                    root + '/review',
                    'POST',
                    { position },
                  )
                  if (response.edit_number !== edit)
                    throw Error('The draft changed. Reload before reviewing.')
                  setReview({ position, original })
                  show(response)
                })
              }}
            >
              Review question
            </button>
          </fieldset>
          {dirty && (
            <p>Save draft edits before requesting another question review.</p>
          )}
        </>
      )}
      {busy && <p role="status">Preparing suggestions…</p>}
      {error && <p role="alert">{error}</p>}
      {output && (
        <div aria-label="Assistance findings">
          <h3>
            {output.provider === 'mock'
              ? 'Mock findings'
              : 'Authoring findings'}
          </h3>
          {review && (
            <blockquote>
              {review.original.stem}
              <ol>
                {review.original.options.map((option, i) => (
                  <li key={i}>{option}</li>
                ))}
              </ol>
            </blockquote>
          )}
          {output.suggestions.map(
            (item, i) =>
              !dismissed.includes(i) && (
                <article key={i}>
                  <h4>{item.focus}</h4>
                  <p>{item.observation}</p>
                  <p>{item.suggestion}</p>
                  <p>{item.assumption}</p>
                  {item.proposed_stem && (
                    <blockquote>{item.proposed_stem}</blockquote>
                  )}
                  {review && item.proposed_stem && (
                    <button
                      disabled={
                        dirty ||
                        JSON.stringify(questions[review.position]) !==
                          JSON.stringify(review.original)
                      }
                      onClick={() => {
                        apply(review.position, item.proposed_stem)
                        dismiss([...dismissed, i])
                      }}
                    >
                      Apply proposed stem
                    </button>
                  )}
                  {!review && (
                    <button
                      type="button"
                      disabled={!navigator.clipboard}
                      onClick={() =>
                        void run(async () => {
                          await navigator.clipboard.writeText(
                            item.observation + '\n' + item.suggestion,
                          )
                        })
                      }
                    >
                      Copy scenario for editing
                    </button>
                  )}
                  <button onClick={() => dismiss([...dismissed, i])}>
                    Dismiss
                  </button>
                </article>
              ),
          )}
        </div>
      )}
    </details>
  )
}
