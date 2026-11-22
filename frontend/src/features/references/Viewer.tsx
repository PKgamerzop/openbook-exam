import { useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy } from 'pdfjs-dist'
import { EventBus, PDFViewer, PDFLinkService, PDFFindController } from 'pdfjs-dist/web/pdf_viewer.mjs'
import 'pdfjs-dist/web/pdf_viewer.css'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = workerUrl
type Outline = NonNullable<Awaited<ReturnType<PDFDocumentProxy['getOutline']>>>

function OutlineList({ items, jump }: { items: Outline; jump: (dest: string | unknown[]) => void }) {
  return <ul>{items.map((item, index) => <li key={index}>
    {item.dest ? <button onClick={() => jump(item.dest!)}>{item.title}</button> : item.title}
    {item.items.length > 0 && <OutlineList items={item.items} jump={jump} />}
  </li>)}</ul>
}

function Thumbnail({ doc, page, jump }: { doc: PDFDocumentProxy; page: number; jump: () => void }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    let active = true
    let task: ReturnType<Awaited<ReturnType<PDFDocumentProxy['getPage']>>['render']> | undefined
    void doc.getPage(page).then(p => {
      if (!active || !canvas.current) return
      const size = p.getViewport({ scale: 1 })
      const viewport = p.getViewport({ scale: 100 / Math.max(size.width, size.height, 1) })
      canvas.current.width = viewport.width
      canvas.current.height = viewport.height
      task = p.render({ canvas: canvas.current, viewport })
      return task.promise
    }).catch(() => undefined)
    return () => { active = false; task?.cancel() }
  }, [doc, page])
  return <button onClick={jump}><canvas ref={canvas} aria-hidden="true" />Page {page}</button>
}

export function Viewer({ url, title, initialPage = 1 }: { url: string; title: string; initialPage?: number }) {
  const root = useRef<HTMLElement>(null)
  const container = useRef<HTMLDivElement>(null)
  const instance = useRef<{ viewer: PDFViewer; links: PDFLinkService; events: EventBus }>(null)
  const [doc, setDoc] = useState<PDFDocumentProxy>()
  const [page, setPage] = useState(initialPage)
  const [scale, setScale] = useState(100)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState('')
  const [outline, setOutline] = useState<Outline>([])
  const [sidebar, setSidebar] = useState('')
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    const element = container.current!
    const events = new EventBus()
    const links = new PDFLinkService({ eventBus: events })
    links.externalLinkEnabled = false
    const find = new PDFFindController({ eventBus: events, linkService: links })
    const viewer = new PDFViewer({ container: element, eventBus: events, linkService: links, findController: find, annotationMode: 0, maxCanvasPixels: 8_000_000 })
    instance.current = { viewer, links, events }
    links.setViewer(viewer)
    const init = () => {
      viewer.currentScaleValue = 'page-width'
      viewer.currentPageNumber = Math.min(initialPage, viewer.pagesCount)
    }
    const updatePage = ({pageNumber}: {pageNumber:number}) => setPage(pageNumber)
    const updateScale = ({scale}: {scale:number}) => setScale(Math.round(scale * 100))
    const updateHits = ({matchesCount}: {matchesCount?: {current:number; total:number}}) =>
      setHits(matchesCount?.total ? `${matchesCount.current} of ${matchesCount.total}` : 'No matches')
    events.on('pagesinit', init)
    events.on('pagechanging', updatePage)
    events.on('scalechanging', updateScale)
    events.on('updatefindmatchescount', updateHits)
    events.on('updatefindcontrolstate', updateHits)
    let active = true
    const loading = getDocument({ url, withCredentials: true })
    void loading.promise.then(async pdf => {
      if (!active) return
      links.setDocument(pdf)
      viewer.setDocument(pdf)
      setDoc(pdf)
      const items = await pdf.getOutline().catch(() => null)
      if (active && items) setOutline(items)
    }).catch(() => { if (active) setError('Unable to open this PDF.') })
    return () => {
      active = false
      events.off('pagesinit', init)
      events.off('pagechanging', updatePage)
      events.off('scalechanging', updateScale)
      events.off('updatefindmatchescount', updateHits)
      events.off('updatefindcontrolstate', updateHits)
      viewer.setDocument(null)
      links.setDocument(null)
      instance.current = null
      void loading.destroy()
    }
  }, [url, initialPage])

  function jump(target: number) {
    if (doc && Number.isInteger(target) && target >= 1 && target <= doc.numPages) {
      instance.current?.viewer.scrollPageIntoView({ pageNumber: target })
    }
  }
  function zoom(value: number | string) {
    const viewer = instance.current?.viewer
    if (!viewer) return
    if (typeof value === 'number') viewer.currentScale = Math.max(.25, Math.min(value, 4))
    else viewer.currentScaleValue = value
  }
  function find(type: string, findPrevious = false) {
    instance.current?.events.dispatch('find', {type, query, findPrevious, highlightAll: true, caseSensitive: false, entireWord: false})
  }

  return <article className={expanded ? 'reader reader-expanded' : 'reader'} ref={root}
    onKeyDown={e => { if (e.key === 'Escape') setExpanded(false) }}>
    <h3>{title}</h3>
    {error && <p role="alert">{error}</p>}
    {!doc && !error && <p role="status">Loading PDF…</p>}
    <fieldset className="reader-toolbar" disabled={!doc}>
      <legend>PDF navigation</legend>
      <button onClick={() => jump(page - 1)} disabled={page <= 1}>Previous page</button>
      <form onSubmit={e => { e.preventDefault(); jump(Number(new FormData(e.currentTarget).get('page'))) }}>
        <label>Page <input key={page} name="page" type="number" min={1} max={doc?.numPages} defaultValue={page} /></label>
        <span>of {doc?.numPages ?? '…'}</span>
        <button>Go</button>
      </form>
      <button onClick={() => jump(page + 1)} disabled={page >= (doc?.numPages ?? 0)}>Next page</button>
      <button onClick={() => zoom(scale / 125)} aria-label="Zoom out">−</button>
      <form onSubmit={e => {e.preventDefault(); zoom(Number(new FormData(e.currentTarget).get('zoom')) / 100)}}>
        <label>Zoom % <input key={scale} name="zoom" type="number" min={25} max={400} defaultValue={scale} /></label>
        <button>Apply zoom</button>
      </form>
      <button onClick={() => zoom(scale / 80)} aria-label="Zoom in">+</button>
      <button onClick={() => zoom('page-width')}>Fit width</button>
      <button onClick={() => zoom('page-fit')}>Fit page</button>
      <button onClick={() => setExpanded(value => !value)}>{expanded ? 'Exit expanded reader' : 'Expand reader'}</button>
    </fieldset>
    <form className="reader-find" onSubmit={e => {e.preventDefault(); find('again')}}>
      <label>Find in this PDF<input value={query} onChange={e => {setQuery(e.target.value); setHits('')}} /></label>
      <button disabled={!doc || !query.trim()}>Next match</button>
      <button type="button" disabled={!doc || !query.trim()} onClick={() => find('again', true)}>Previous match</button>
      <output aria-live="polite">{hits}</output>
    </form>
    <div className="reader-panels">
      <div className="reader-sidebar">
        <button aria-expanded={sidebar === 'pages'} disabled={!doc} onClick={() => setSidebar(sidebar === 'pages' ? '' : 'pages')}>Thumbnails</button>
        {!!outline.length && <button aria-expanded={sidebar === 'outline'} onClick={() => setSidebar(sidebar === 'outline' ? '' : 'outline')}>Outline</button>}
        {sidebar === 'pages' && doc && <div className="reader-thumbnails">{Array.from({length: doc.numPages}, (_, i) =>
          Math.abs(page - i - 1) <= 6
            ? <Thumbnail key={i} doc={doc} page={i+1} jump={() => jump(i+1)} />
            : <button key={i} onClick={() => jump(i+1)}>Page {i+1}</button>)}</div>}
        {sidebar === 'outline' && <OutlineList items={outline} jump={dest => {void instance.current?.links.goToDestination(dest)}} />}
      </div>
      <div className="reader-scroll">
        <div className="pdf-scroll-container" ref={container} tabIndex={0} aria-label={title + ' pages'}>
          <div className="pdfViewer" />
        </div>
      </div>
    </div>
  </article>
}
