import { PDFDocument, rgb } from 'pdf-lib'

export async function createFixtures() {
  const textDocument = await PDFDocument.create()
  textDocument.addPage([520, 340]).drawText('Page one contains only the introduction.', {
    x: 35, y: 285, size: 16,
  })
  textDocument.addPage([520, 340]).drawText('A helix appears on the second page.', {
    x: 35, y: 285, size: 16,
  })

  const columns = await PDFDocument.create()
  const page = columns.addPage([520, 340])
  page.drawText('Fractal', { x: 35, y: 285, size: 18 })
  page.drawText('Left column notes', { x: 35, y: 252, size: 14 })
  page.drawText('Catalyst', { x: 285, y: 285, size: 18 })
  page.drawText('Right column notes', { x: 285, y: 252, size: 14 })

  const scanned = await PDFDocument.create()
  const image = await scanned.embedPng(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg==',
  )
  const scanPage = scanned.addPage([520, 340])
  scanPage.drawRectangle({ x: 35, y: 65, width: 450, height: 210, color: rgb(0.9, 0.92, 0.94) })
  scanPage.drawImage(image, { x: 35, y: 65, width: 450, height: 210 })

  return [
    { id: 'handbook', title: 'Synthetic handbook', bytes: await textDocument.save() },
    { id: 'columns', title: 'Synthetic two-column notes', bytes: await columns.save() },
    { id: 'scanned', title: 'Synthetic image-only page', bytes: await scanned.save() },
  ]
}
