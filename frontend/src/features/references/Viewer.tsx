import { useEffect, useEffectEvent, useRef, useState, type ReactNode } from 'react'
import { Icon } from '../../app/Icon'
import {
  getDocument,
  GlobalWorkerOptions,
  type PDFDocumentProxy,
} from 'pdfjs-dist'
import {
  EventBus,
  FindState,
  PDFViewer,
  PDFLinkService,
  PDFFindController,
} from 'pdfjs-dist/web/pdf_viewer.mjs'
import 'pdfjs-dist/web/pdf_viewer.css'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = workerUrl
type Outline = NonNullable<Awaited<ReturnType<PDFDocumentProxy['getOutline']>>>

function OutlineList({
  items,
  jump,
}: {
  items: Outline
  jump: (dest: string | unknown[]) => void
}) {
  return (
    <ul>
      {items.map((item, index) => (
        <li key={index}>
          {item.dest ? (
            <button onClick={() => jump(item.dest!)}>{item.title}</button>
          ) : (
            item.title
          )}
          {item.items.length > 0 && (
            <OutlineList items={item.items} jump={jump} />
          )}
        </li>
      ))}
    </ul>
  )
}

function Thumbnail({
  doc,
  page,
  jump,
  selected,
}: {
  doc: PDFDocumentProxy
  page: number
  jump: () => void
  selected: boolean
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    let active = true
    let task:
      | ReturnType<Awaited<ReturnType<PDFDocumentProxy['getPage']>>['render']>
      | undefined
    void doc
      .getPage(page)
      .then((p) => {
        if (!active || !canvas.current) return
        const size = p.getViewport({ scale: 1 })
        const viewport = p.getViewport({
          scale: 100 / Math.max(size.width, size.height, 1),
        })
        canvas.current.width = viewport.width
        canvas.current.height = viewport.height
        task = p.render({ canvas: canvas.current, viewport })
        return task.promise
      })
      .catch(() => undefined)
    return () => {
      active = false
      task?.cancel()
    }
  }, [doc, page])
  return (
    <button onClick={jump} aria-current={selected ? 'page' : undefined}>
      <canvas ref={canvas} aria-hidden="true" />
      Page {page}
    </button>
  )
}

export function Viewer({
  url,
  title,
  navigation,
  tools,
  onPage,
  allowExport = true,
  focusOnOpen = false,
}: {
  url: string
  title: string
  navigation?: { page: number; sequence: number }
  tools?: ReactNode
  onPage?: (page: number) => void
  allowExport?: boolean
  focusOnOpen?: boolean
}) {
  const root = useRef<HTMLElement>(null)
  const container = useRef<HTMLDivElement>(null)
  const instance = useRef<{
    viewer: PDFViewer
    links: PDFLinkService
    events: EventBus
  }>(null)
  const [doc, setDoc] = useState<PDFDocumentProxy>()
  const [page, setPage] = useState(navigation?.page ?? 1)
  const [scale, setScale] = useState(100)
  const [zoomPreset, setZoomPreset] = useState<string>()
  const [error, setError] = useState('')
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState('')
  const [outline, setOutline] = useState<Outline>([])
  const [sidebar, setSidebar] = useState('')
  const [expanded, setExpanded] = useState(false)
  const requestedPage = useEffectEvent(() => navigation?.page ?? 1)
  const expandedButton = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!focusOnOpen) return
    root.current?.focus({ preventScroll: true })
    root.current?.scrollIntoView({ block: 'nearest' })
  }, [focusOnOpen, navigation?.sequence])

  useEffect(() => {
    const element = container.current!
    const events = new EventBus()
    const links = new PDFLinkService({ eventBus: events })
    links.externalLinkEnabled = false
    const find = new PDFFindController({ eventBus: events, linkService: links })
    const viewer = new PDFViewer({
      container: element,
      eventBus: events,
      linkService: links,
      findController: find,
      annotationMode: 0,
      maxCanvasPixels: 8_000_000,
    })
    instance.current = { viewer, links, events }
    links.setViewer(viewer)
    const resize = new ResizeObserver(() => {
      const fit = viewer.currentScaleValue
      if (element.clientWidth && element.clientHeight && viewer.pagesCount && (fit === 'page-width' || fit === 'page-fit')) {
        viewer.currentScaleValue = fit
      }
    })
    resize.observe(element)
    const init = () => {
      viewer.currentScaleValue = 'page-width'
      viewer.currentPageNumber = Math.min(requestedPage(), viewer.pagesCount)
    }
    const updatePage = ({ pageNumber }: { pageNumber: number }) =>
      setPage(pageNumber)
    const updateScale = ({ scale, presetValue }: { scale: number; presetValue?: string }) => {
      setScale(Math.round(scale * 100))
      setZoomPreset(presetValue === 'page-fit' || presetValue === 'page-width' ? presetValue : undefined)
    }
    const updateHits = ({
      matchesCount,
      state,
    }: {
      matchesCount?: { current: number; total: number }
      state?: number
    }) => {
      if (state === FindState.PENDING) setHits('Finding…')
      else if (matchesCount?.total) setHits(`${matchesCount.current} of ${matchesCount.total}`)
      else if (state === FindState.NOT_FOUND) setHits('No matches')
    }
    events.on('pagesinit', init)
    events.on('pagechanging', updatePage)
    events.on('scalechanging', updateScale)
    events.on('updatefindmatchescount', updateHits)
    events.on('updatefindcontrolstate', updateHits)
    let active = true
    const loading = getDocument({ url, withCredentials: true })
    void loading.promise
      .then(async (pdf) => {
        if (!active) return
        links.setDocument(pdf)
        viewer.setDocument(pdf)
        setDoc(pdf)
        const items = await pdf.getOutline().catch(() => null)
        if (active && items) setOutline(items)
      })
      .catch(() => {
        if (active) setError('Unable to open this PDF.')
      })
    return () => {
      active = false
      resize.disconnect()
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
  }, [url, loadAttempt])

  useEffect(() => {
    const viewer = instance.current?.viewer
    if (navigation && viewer?.getPageView(navigation.page - 1))
      viewer.scrollPageIntoView({ pageNumber: navigation.page })
  }, [navigation])

  useEffect(() => {
    if (!expanded) return
    const hidden: HTMLElement[] = []
    for (let child = root.current; child && child !== document.body; child = child.parentElement) {
      for (const sibling of child.parentElement?.children ?? []) {
        if (sibling !== child && sibling instanceof HTMLElement && !sibling.inert) {
          sibling.inert = true
          hidden.push(sibling)
        }
      }
    }
    function close(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      setExpanded(false)
      expandedButton.current?.focus()
    }
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('keydown', close)
      for (const element of hidden) element.inert = false
    }
  }, [expanded])

  useEffect(() => {
    onPage?.(page)
  }, [page, onPage])

  function jump(target: number) {
    if (
      doc &&
      Number.isInteger(target) &&
      target >= 1 &&
      target <= doc.numPages
    ) {
      instance.current?.viewer.scrollPageIntoView({ pageNumber: target })
    }
  }
  function zoom(value: number | string) {
    const viewer = instance.current?.viewer
    if (!viewer) return
    if (typeof value === 'number')
      viewer.currentScale = Math.max(0.25, Math.min(value, 4))
    else viewer.currentScaleValue = value
  }
  function find(type: string, findPrevious = false) {
    instance.current?.events.dispatch('find', {
      type,
      query,
      findPrevious,
      highlightAll: true,
      caseSensitive: false,
      entireWord: false,
    })
  }

  return (
    <article
      className={expanded ? 'reader reader-expanded' : 'reader'}
      ref={root}
      tabIndex={focusOnOpen ? -1 : undefined}
      aria-label={title + ' PDF reader'}
      role={expanded ? 'dialog' : undefined}
      aria-modal={expanded || undefined}
    >
      <div className="reader-heading">
        <h3>{title}</h3>
        <button type="button" ref={expandedButton} className="button-quiet icon-button"
          aria-label={expanded ? 'Exit expanded reader' : 'Expand reader'}
          title={expanded ? 'Exit expanded reader' : 'Expand reader'}
          aria-pressed={expanded} onClick={() => setExpanded((value) => !value)}>
          <Icon name={expanded ? 'shrink' : 'expand'} />
        </button>
      </div>
      {allowExport && doc && (
        <div className="reader-export">
          <a href={url} target="_blank" rel="noreferrer">Open printable PDF</a>
          <a href={url} download={title + '.pdf'}>Download PDF</a>
        </div>
      )}
      {error && (
        <div className="reader-message">
          <p role="alert">{error}</p>
          <button onClick={() => {
            setError('')
            setLoadAttempt((attempt) => attempt + 1)
          }}>Retry PDF</button>
        </div>
      )}
      {!doc && !error && <p className="reader-message" role="status">Loading PDF…</p>}
      <fieldset className="reader-toolbar" disabled={!doc}>
        <legend className="sr-only">PDF navigation</legend>
        <div className="reader-controls">
          <div className="reader-control-group">
            <button className="button-quiet icon-button" onClick={() => jump(page - 1)}
              disabled={page <= 1} aria-label="Previous page" title="Previous page"><Icon name="left" /></button>
            <form onSubmit={(e) => {
              e.preventDefault()
              jump(Number(new FormData(e.currentTarget).get('page')))
            }}>
              <label>
                <span className="sr-only">Page</span>
                <input key={page} name="page" type="number" min={1} max={doc?.numPages} defaultValue={page} />
              </label>
              <span>of {doc?.numPages ?? '…'}</span>
              <button className="button-quiet">Go</button>
            </form>
            <button className="button-quiet icon-button" onClick={() => jump(page + 1)}
              disabled={page >= (doc?.numPages ?? 0)} aria-label="Next page" title="Next page"><Icon name="right" /></button>
          </div>
          <div className="reader-control-group">
            <button className="button-quiet icon-button" onClick={() => zoom(scale / 125)}
              disabled={scale <= 25} aria-label="Zoom out" title="Zoom out"><Icon name="minus" /></button>
            <label className="zoom-select">
              <span className="sr-only">Zoom level</span>
              <select value={zoomPreset ?? String(scale)} onChange={(e) => {
                const value = e.target.value
                zoom(Number.isNaN(Number(value)) ? value : Number(value) / 100)
              }}>
                <option value="page-width">Fit width</option>
                <option value="page-fit">Fit page</option>
                {[...new Set([scale, 50, 75, 100, 125, 150, 200, 300, 400])].sort((a, b) => a - b)
                  .map((level) => <option key={level} value={level}>{level}%</option>)}
              </select>
            </label>
            <button className="button-quiet icon-button" onClick={() => zoom(scale / 80)}
              disabled={scale >= 400} aria-label="Zoom in" title="Zoom in"><Icon name="plus" /></button>
          </div>
        </div>
      </fieldset>
      <form className="reader-find" onSubmit={(e) => {
        e.preventDefault()
        if (query.trim()) find('again')
      }}>
        <label>
          <span className="sr-only">Find in this PDF</span>
          <input type="search" placeholder="Find in this PDF" value={query} disabled={!doc}
            onChange={(e) => {
              setQuery(e.target.value)
              setHits('')
              if (!e.target.value) instance.current?.events.dispatch('findbarclose', {})
            }} />
        </label>
        <output aria-live="polite">{hits}</output>
        <button className="button-quiet icon-button" type="button" disabled={!doc || !query.trim()}
          onClick={() => find('again', true)} aria-label="Previous match" title="Previous match"><Icon name="left" /></button>
        <button className="button-quiet icon-button" disabled={!doc || !query.trim()}
          aria-label="Next match" title="Next match"><Icon name="right" /></button>
      </form>
      <div className="reader-extras">
        <button className="button-quiet" aria-expanded={sidebar === 'pages'} disabled={!doc}
          onClick={() => setSidebar(sidebar === 'pages' ? '' : 'pages')}>
          <Icon name="grid" /> Thumbnails
        </button>
        {!!outline.length && <button className="button-quiet" aria-expanded={sidebar === 'outline'}
          onClick={() => setSidebar(sidebar === 'outline' ? '' : 'outline')}>Outline</button>}
        {doc && tools}
      </div>
      <div className={sidebar ? 'reader-panels sidebar-open' : 'reader-panels'}>
        {sidebar && <div className="reader-sidebar">
          {sidebar === 'pages' && doc && (
            <div className="reader-thumbnails">
              {Array.from({ length: doc.numPages }, (_, i) =>
                Math.abs(page - i - 1) <= 6 ? (
                  <Thumbnail key={i} doc={doc} page={i + 1} selected={i + 1 === page} jump={() => jump(i + 1)} />
                ) : (
                  <button key={i} onClick={() => jump(i + 1)}>Page {i + 1}</button>
                ),
              )}
            </div>
          )}
          {sidebar === 'outline' && <OutlineList items={outline} jump={(dest) => {
            void instance.current?.links.goToDestination(dest)
          }} />}
        </div>}
        <div className="reader-scroll">
          <div className="pdf-scroll-container" ref={container} tabIndex={0} aria-label={title + ' pages'}>
            <div className="pdfViewer" />
          </div>
        </div>
      </div>
    </article>
  )
}
