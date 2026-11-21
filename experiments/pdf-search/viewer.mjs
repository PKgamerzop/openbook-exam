import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = workerUrl
const hitsList = document.querySelector('#hits')
const status = document.querySelector('#status')
const canvas = document.querySelector('#page')

async function openPage(id, title, number) {
  const buttons = hitsList.querySelectorAll('button')
  buttons.forEach(button => { button.disabled = true })
  const loadingTask = getDocument({ url: `/generated/${id}.pdf` })
  try {
    const pdf = await loadingTask.promise
    const page = await pdf.getPage(number)
    const viewport = page.getViewport({ scale: 1 })
    canvas.width = viewport.width
    canvas.height = viewport.height
    await page.render({ canvas, viewport }).promise
    status.textContent = `Showing ${title}, page ${page.pageNumber}`
  } catch {
    status.textContent = 'The PDF page could not be opened.'
  } finally {
    try {
      await loadingTask.destroy()
    } finally {
      buttons.forEach(button => { button.disabled = false })
    }
  }
}

function addPageLink(id, title, number, label) {
  const row = document.createElement('li')
  const button = document.createElement('button')
  button.textContent = label
  button.addEventListener('click', () => { void openPage(id, title, number) })
  row.append(button)
  hitsList.append(row)
}

try {
  const response = await fetch('/generated/results.json')
  if (!response.ok) throw new Error('Results missing')
  const { keyword, documents, hits } = await response.json()
  status.textContent = `${hits.length} hits for “${keyword}”.`
  for (const hit of hits) {
    const { id, title } = documents.find(doc => doc.id === hit.document_id)
    addPageLink(id, title, hit.page_number, `${title}, page ${hit.page_number} — ${hit.page_text}`)
  }
  for (const { id, title } of documents.filter(doc => !doc.searchable)) {
    addPageLink(id, title, 1, `${title} — view only`)
  }
} catch {
  status.textContent = 'Run npm test to generate the experiment results.'
}
