import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'
import pg from 'pg'
import { createFixtures } from './fixtures.mjs'

const fontDirectory = new URL('./node_modules/pdfjs-dist/standard_fonts/', import.meta.url)
const standardFontDataUrl = fileURLToPath(fontDirectory).replaceAll('\\', '/')
const client = new pg.Client({
  host: process.env.POSTGRES_HOST || '127.0.0.1',
  port: Number(process.env.POSTGRES_PORT || 5432),
  database: process.env.POSTGRES_DB,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  connectionTimeoutMillis: 3000,
})

const fixtures = await createFixtures()
const documents = []
await client.connect()
try {
  await client.query(`
    CREATE TEMP TABLE pdf_pages (
      document_id text NOT NULL,
      page_number integer NOT NULL,
      page_text text NOT NULL,
      search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', page_text)) STORED,
      PRIMARY KEY (document_id, page_number)
    );
    CREATE INDEX ON pdf_pages USING gin (search_vector);
  `)

  for (const { id, title, bytes } of fixtures) {
    const loadingTask = getDocument({ data: bytes.slice(), standardFontDataUrl })
    let searchable = false
    try {
      const pdf = await loadingTask.promise
      for (let number = 1; number <= pdf.numPages; number++) {
        const page = await pdf.getPage(number)
        const content = await page.getTextContent()
        const text = content.items.flatMap(item => 'str' in item ? [item.str] : []).join(' ').trim()
        if (text) {
          searchable = true
          await client.query('INSERT INTO pdf_pages VALUES ($1, $2, $3)', [id, number, text])
        }
      }
    } finally {
      await loadingTask.destroy()
    }
    documents.push({ id, title, searchable })
  }

  async function search(keyword) {
    const { rows } = await client.query(`
      SELECT document_id, page_number, page_text
      FROM pdf_pages
      WHERE search_vector @@ websearch_to_tsquery('english', $1)
      ORDER BY document_id, page_number
    `, [keyword])
    return rows
  }

  for (const [keyword, document, page] of [
    ['helix', 'handbook', 2],
    ['fractal', 'columns', 1],
    ['catalyst', 'columns', 1],
  ]) {
    const hits = await search(keyword)
    assert.deepEqual(hits.map(row => [row.document_id, row.page_number]), [[document, page]])
    console.log(`${keyword}: ${document}, page ${page}`)
  }
  assert.deepEqual(await search('termabsentfromallfixtures'), [])
  assert.equal(documents.find(doc => doc.id === 'scanned').searchable, false)
  console.log('Image-only fixture: view-only. Absent keyword: no hits.')

  const keyword = process.argv.slice(2).join(' ') || 'helix'
  const output = new URL('./public/generated/', import.meta.url)
  await mkdir(output, { recursive: true })
  await Promise.all(fixtures.map(({ id, bytes }) => writeFile(new URL(`${id}.pdf`, output), bytes)))
  await writeFile(new URL('results.json', output), JSON.stringify({ keyword, documents, hits: await search(keyword) }))
} finally {
  await client.end()
}
