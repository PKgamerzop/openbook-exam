import { lazy, Suspense, useState } from 'react'
import { api, useResource, useAction } from '../../app/api'
import { Icon } from '../../app/Icon'

const Viewer = lazy(() =>
  import('./Viewer').then((module) => ({ default: module.Viewer })),
)

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

type Mark = { version_id: number; page: number; name: string; pinned: boolean }

export function Resources({ path }: { path: string }) {
  const { data, error } = useResource<Reference[]>(path)
  const [query, setQuery] = useState('')
  const [search, submit] = useState<string>()
  const [selection, open] = useState<{
    id: number
    page: number
    sequence: number
  }>()
  const [offset, paginate] = useState(0)
  const [activePage, setActivePage] = useState(1)
  const [markRefresh, reloadMarks] = useState(0)
  const exportPolicy = useResource<{ allowed: boolean }>(
    data?.length ? path + '/export-policy' : '',
  )
  const marks = useResource<Mark[]>(
    data?.length ? path + '/marks' : '',
    markRefresh,
  )
  const { run: markAction, busy: markBusy, error: markError } = useAction()
  const selected = selection ?? (data?.[0] && { id: data[0].id, page: 1, sequence: 0 })
  const selectedDoc = data?.find((d) => d.id === selected?.id)
  const currentMark = marks.data?.find((m) => m.version_id === selectedDoc?.id && m.page === activePage)
  function jump(id: number, page: number) {
    setActivePage(page)
    open((s) => ({ id, page, sequence: (s?.sequence ?? 0) + 1 }))
  }
  if (error) return <p role="alert">{error}</p>
  if (!data) return <p>Loading references…</p>
  if (!data.length) return <p>No references selected.</p>
  return (
    <div className="reference-panel">
      <label className="reference-select">
        <span><Icon name="file" /> Reference document</span>
        <select value={selected?.id} onChange={(event) => jump(Number(event.target.value), 1)}>
          {data.map((d) => (
            <option key={d.id} value={d.id}>{d.title} · v{d.number}{d.status === 'view-only' ? ' · View only' : ''}</option>
          ))}
        </select>
      </label>
      <form
        className="reference-toolbar reference-search"
        onSubmit={(e) => {
          e.preventDefault()
          submit(query.trim())
          paginate(0)
        }}
      >
        <label>
          <span className="sr-only">Search all permitted PDFs</span>
          <input
            type="search"
            maxLength={160}
            placeholder="Search all permitted PDFs"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button className="button-secondary icon-button" aria-label="Search references" title="Search references"><Icon name="search" /></button>
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
          clear={() => {
            submit(undefined)
            setQuery('')
          }}
          offset={offset}
          paginate={paginate}
        />
      )}
      <details className="reference-bookmarks">
        <summary><Icon name="bookmark" /> Bookmarks and pinned pages {marks.data?.length ? <span>{marks.data.length}</span> : null}</summary>
        {marks.data && !marks.data.length && <p className="muted">No saved pages.</p>}
        {!marks.data && !marks.error && <p role="status">Loading saved pages…</p>}
        {data.map((d) => {
          const saved = marks.data?.filter((m) => m.version_id === d.id)
            .sort((a, b) => Number(b.pinned) - Number(a.pinned) || a.page - b.page) ?? []
          if (!saved.length) return null
          return (
            <div key={d.id}>
              <h4>{d.title}</h4>
              <ul>
                {saved.map((m) => (
                  <li key={m.page}>
                    <button className="button-quiet" onClick={() => jump(d.id, m.page)}>
                      {m.name || 'Page ' + m.page}
                      {m.pinned ? ' · pinned' : ''}
                    </button>
                    <button
                      className="button-secondary"
                      disabled={markBusy}
                      onClick={() =>
                        void markAction(async () => {
                          await api(
                            path + '/marks/' + d.id + '/' + m.page,
                            'PUT',
                            { name: m.name, pinned: !m.pinned },
                          )
                          reloadMarks((n) => n + 1)
                        })
                      }
                    >
                      {m.pinned ? 'Unpin' : 'Pin'}
                    </button>
                    <button
                      className="button-quiet"
                      disabled={markBusy}
                      onClick={() =>
                        void markAction(async () => {
                          await api(
                            path + '/marks/' + d.id + '/' + m.page,
                            'DELETE',
                          )
                          reloadMarks((n) => n + 1)
                        })
                      }
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </details>
      {(marks.error || markError) && (
        <div>
          <p role="alert">{marks.error || markError}</p>
          {marks.error && (
            <button className="button-secondary" onClick={() => reloadMarks((n) => n + 1)}>
              Retry saved pages
            </button>
          )}
        </div>
      )}
      {selectedDoc && selected && (
        <Suspense fallback={<p role="status">Loading PDF reader…</p>}>
          <Viewer
            key={selectedDoc.id}
            title={selectedDoc.title}
            navigation={selected}
            focusOnOpen={!!selected.sequence}
            onPage={setActivePage}
            allowExport={exportPolicy.data?.allowed === true}
            url={'/api' + path + '/' + selected.id + '/file'}
            tools={marks.data && (
              <details className="bookmark-editor" key={activePage}>
                <summary>
                  <Icon name="bookmark" /> {currentMark ? 'Edit bookmark' : 'Bookmark page ' + activePage}
                </summary>
                <form
                  className="reference-toolbar mark-form"
                  onSubmit={(e) => {
                    e.preventDefault()
                    const fields = new FormData(e.currentTarget)
                    void markAction(async () => {
                      await api(path + '/marks/' + selectedDoc.id + '/' + activePage, 'PUT', {
                        name: String(fields.get('name') ?? ''),
                        pinned: fields.has('pin'),
                      })
                      reloadMarks((n) => n + 1)
                    })
                  }}
                >
                  <label>
                    Bookmark name
                    <input name="name" maxLength={100} defaultValue={currentMark?.name} placeholder={`Page ${activePage}`} />
                  </label>
                  <label>
                    <input type="checkbox" name="pin" defaultChecked={currentMark?.pinned} /> Pin page
                  </label>
                  <button disabled={markBusy}>{currentMark ? 'Update bookmark' : 'Save bookmark'}</button>
                </form>
              </details>
            )}
          />
        </Suspense>
      )}
    </div>
  )
}
function Hits({
  path,
  jump,
  clear,
  offset,
  paginate,
}: {
  path: string
  jump: (id: number, page: number) => void
  clear: () => void
  offset: number
  paginate: (n: number) => void
}) {
  const result =
    useResource<(Reference & { page: number; snippet: string })[]>(path)
  return (
    <div
      className="reference-hits"
      role="region"
      aria-label="Reference search results"
      tabIndex={0}
    >
      <div className="reference-hit-heading">
        <strong>Search results</strong>
        <button className="button-quiet icon-button" aria-label="Clear search" title="Clear search" onClick={clear}><Icon name="close" /></button>
      </div>
      {result.error && <p role="alert">{result.error}</p>}
      {!result.data && !result.error && <p role="status">Searching…</p>}
      {result.data?.length === 0 && <p>No matching pages.</p>}
      {result.data?.map((h) => (
        <div key={h.id + '-' + h.page}>
          <button className="button-quiet" onClick={() => jump(h.id, h.page)}>
            {h.title} · page {h.page}
          </button>
          <p>{h.snippet}</p>
        </div>
      ))}
      {offset > 0 && (
        <button onClick={() => paginate(offset - 30)}>Previous results</button>
      )}
      {result.data?.length === 30 && (
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
            <button
              aria-pressed={preview?.id === d.id}
              onClick={() => setPreview(d)}
            >
              Preview {d.title}
            </button>
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
        <Suspense fallback={<p role="status">Loading PDF reader…</p>}>
          <Viewer
            key={preview.id}
            url={'/api' + path + '/' + preview.id + '/file'}
            title={preview.title}
            focusOnOpen
          />
        </Suspense>
      )}
    </article>
  )
}
