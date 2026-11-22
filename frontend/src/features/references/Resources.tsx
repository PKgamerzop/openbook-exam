import { useState } from 'react'
import { api, useResource, useAction } from '../../app/api'
import { Viewer } from './Viewer'

export type Reference = {
  id: number
  document_id: number
  number: number
  title: string
  filename: string
  pages: number
  size: number
  status: string
  folder: string
  topics: string[]
}
export const libraryPath = (cid: number) =>
  '/lecturer/courses/' + cid + '/references'

export function Resources({ path }: { path: string }) {
  const { data, error } = useResource<Reference[]>(path)
  const [query, setQuery] = useState('')
  const [search, submit] = useState<string>()
  const [selected, open] = useState<{
    id: number
    page: number
    sequence: number
  }>()
  const [offset, paginate] = useState(0)
  const selectedDoc = data?.find((d) => d.id === selected?.id)
  function jump(id: number, page: number) {
    open((s) => ({ id, page, sequence: (s?.sequence ?? 0) + 1 }))
  }
  if (error) return <p role="alert">{error}</p>
  if (!data) return <p>Loading references…</p>
  if (!data.length) return <p>No references selected.</p>
  return (
    <div className="reference-panel">
      <h3>Exam references</h3>
      <div className="reference-actions">
        {data.map((d) => (
          <button key={d.id} onClick={() => jump(d.id, 1)}>
            {d.title} · v{d.number} · {d.status}
          </button>
        ))}
      </div>
      <form
        className="reference-toolbar"
        onSubmit={(e) => {
          e.preventDefault()
          submit(query.trim())
          paginate(0)
        }}
      >
        <label>
          Search all permitted PDFs
          <input
            type="search"
            maxLength={160}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button>Search references</button>
      </form>
      {search === '' && <p>Enter a keyword.</p>}
      {search && (
        <Hits
          path={
            path +
            '/search?' +
            new URLSearchParams({ q: search, offset: String(offset) })
          }
          jump={jump}
          offset={offset}
          paginate={paginate}
        />
      )}
      {selected && selectedDoc && (
        <Viewer
          key={selected.sequence}
          title={selectedDoc.title}
          initialPage={selected.page}
          url={'/api' + path + '/' + selected.id + '/file'}
        />
      )}
    </div>
  )
}
function Hits({
  path,
  jump,
  offset,
  paginate,
}: {
  path: string
  jump: (id: number, page: number) => void
  offset: number
  paginate: (n: number) => void
}) {
  const result =
    useResource<(Reference & { page: number; snippet: string })[]>(path)
  if (result.error) return <p role="alert">{result.error}</p>
  if (!result.data) return <p>Searching…</p>
  return (
    <div>
      {!result.data.length && <p>No matching pages.</p>}
      {result.data.map((h) => (
        <div key={h.id + '-' + h.page}>
          <button onClick={() => jump(h.id, h.page)}>
            {h.title} · page {h.page}
          </button>
          <p>{h.snippet}</p>
        </div>
      ))}
      {offset > 0 && (
        <button onClick={() => paginate(offset - 30)}>Previous results</button>
      )}
      {result.data.length === 30 && (
        <button onClick={() => paginate(offset + 30)}>More results</button>
      )}
    </div>
  )
}

export function Library({ cid }: { cid: number }) {
  const path = libraryPath(cid)
  const [refresh, reload] = useState(0)
  const { data, error } = useResource<Reference[]>(path, refresh)
  const { run, busy, error: actionError } = useAction()
  const [filter, setFilter] = useState('')
  const [preview, setPreview] = useState<Reference>()
  const [target, setTarget] = useState('')
  const [file, setFile] = useState<File>()
  const [title, setTitle] = useState('')
  const [folder, setFolder] = useState('General')
  const [inputKey, resetInput] = useState(0)
  const docs = data?.filter((d) =>
    [d.title, d.filename, d.folder, ...d.topics]
      .join(' ')
      .toLowerCase()
      .includes(filter.toLowerCase()),
  )
  return (
    <article className="reference-library">
      <h3>Reference Library</h3>
      <form
        className="upload-grid"
        onSubmit={(e) => {
          e.preventDefault()
          void run(async () => {
            if (!file) return
            const params = new URLSearchParams({
              title,
              filename: file.name,
              folder,
            })
            if (target) params.set('document_id', target)
            const response = await fetch('/api' + path + '?' + params, {
              method: 'POST',
              headers: { 'X-OpenBook-Request': '1' },
              body: file,
            })
            if (!response.ok) throw Error((await response.json()).detail)
            reload((n) => n + 1)
            setFile(undefined)
            setTitle('')
            resetInput((n) => n + 1)
          })
        }}
      >
        <label>
          Upload destination
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="">New document</option>
            {data
              ?.filter(
                (d, i, a) =>
                  a.findIndex((x) => x.document_id === d.document_id) === i,
              )
              .map((d) => (
                <option value={d.document_id} key={d.id}>
                  New version of {d.title}
                </option>
              ))}
          </select>
        </label>
        <label>
          PDF file
          <input
            key={inputKey}
            required
            type="file"
            accept="application/pdf"
            onChange={(e) => {
              const f = e.target.files?.[0]
              setFile(f)
              setTitle(f?.name.replace(/\.pdf$/i, '') ?? '')
            }}
          />
        </label>
        <label>
          Display title
          <input
            required
            maxLength={160}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        {!target && (
          <label>
            Library folder
            <input
              required
              maxLength={160}
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
            />
          </label>
        )}
        <button disabled={busy}>Upload PDF</button>
      </form>
      <div className="reference-toolbar">
        <label>
          Filter by title, filename, folder or topic
          <input
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </label>
        <button onClick={() => reload((n) => n + 1)}>Refresh library</button>
      </div>
      {(error || actionError) && <p role="alert">{error || actionError}</p>}
      {!data && !error && <p>Loading library…</p>}
      {docs?.length === 0 && <p>No matching documents.</p>}
      <div className="library-grid">
        {docs?.map((d) => (
          <div className="library-entry" key={d.id}>
            <div className="library-entry-heading">
              <h4>
                {d.title} · v{d.number}
              </h4>
              <span className="processing-status" data-status={d.status}>
                {d.status}
              </span>
            </div>
            <p>
              {d.filename} · {Math.ceil(d.size / 1024)} KiB · {d.pages} pages
            </p>
            <p>
              {d.folder} {d.topics.join(' · ')}
            </p>
            <button onClick={() => setPreview(d)}>Preview {d.title}</button>
            {d.status === 'failed' && (
              <button
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await api(path + '/' + d.id + '/retry', 'POST')
                    reload((n) => n + 1)
                  })
                }
              >
                Retry indexing
              </button>
            )}
            <details>
              <summary>Organize document</summary>
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  const f = new FormData(e.currentTarget)
                  void run(async () => {
                    await api(path + '/documents/' + d.document_id, 'PUT', {
                      folder: f.get('folder'),
                      topics: String(f.get('topics'))
                        .split(',')
                        .map((x) => x.trim())
                        .filter(Boolean),
                    })
                    reload((n) => n + 1)
                  })
                }}
              >
                <label>
                  Folder
                  <input required name="folder" defaultValue={d.folder} />
                </label>
                <label>
                  Topics, comma-separated
                  <input name="topics" defaultValue={d.topics.join(', ')} />
                </label>
                <button disabled={busy}>Save organization</button>
              </form>
            </details>
          </div>
        ))}
      </div>
      {preview && (
        <Viewer
          key={preview.id}
          url={'/api' + path + '/' + preview.id + '/file'}
          title={preview.title}
        />
      )}
    </article>
  )
}
