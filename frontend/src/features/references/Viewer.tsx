import { useEffect, useRef, useState } from 'react'
import {
  getDocument,
  GlobalWorkerOptions,
  type PDFDocumentProxy,
  type RenderTask,
} from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = workerUrl

export function Viewer({
  url,
  title,
  initialPage = 1,
}: {
  url: string
  title: string
  initialPage?: number
}) {
  const [doc, setDoc] = useState<PDFDocumentProxy>()
  const [page, setPage] = useState(initialPage)
  const [error, setError] = useState('')
  const [rendered, setRendered] = useState(0)
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    let active = true
    const loading = getDocument({ url, withCredentials: true })
    loading.promise
      .then((pdf) => active && setDoc(pdf))
      .catch(() => active && setError('Unable to open this PDF.'))
    return () => {
      active = false
      void loading.destroy()
    }
  }, [url])
  useEffect(() => {
    if (!doc) return
    let active = true
    let task: RenderTask | undefined
    doc
      .getPage(page)
      .then(async (p) => {
        if (!active || !canvas.current) return
        const dimensions = p.getViewport({ scale: 1 })
        const viewport = p.getViewport({
          scale: Math.min(
            1.4,
            1200 / Math.max(dimensions.width, dimensions.height, 1),
          ),
        })
        canvas.current.width = viewport.width
        canvas.current.height = viewport.height
        task = p.render({ canvas: canvas.current, viewport })
        await task.promise
        if (active) setRendered(page)
      })
      .catch(() => active && setError('Unable to render this page.'))
    return () => {
      active = false
      task?.cancel()
    }
  }, [doc, page])
  return (
    <article className="pdf-view">
      <h3>{title}</h3>
      {error ? (
        <p role="alert">{error}</p>
      ) : (
        <>
          <nav aria-label="PDF pages">
            <button
              disabled={!doc || page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Previous page
            </button>
            <span aria-live="polite">
              Page {page} of {doc?.numPages ?? '…'}
            </span>
            <button
              disabled={!doc || page >= doc.numPages}
              onClick={() => setPage(page + 1)}
            >
              Next page
            </button>
          </nav>
          {rendered !== page && <p role="status">Loading page…</p>}
          <canvas
            key={page}
            ref={canvas}
            aria-label={title + ', page ' + page}
            hidden={rendered !== page}
          />
        </>
      )}
    </article>
  )
}
