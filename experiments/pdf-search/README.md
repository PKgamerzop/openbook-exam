# PDF search feasibility experiment

This standalone experiment generates synthetic PDFs, extracts their text with PDF.js, then searches the text by page with PostgreSQL full-text search and a GIN index. A small viewer renders the selected hit with PDF.js. It runs outside the OpenBook application and uses a session-scoped temporary table.

## Reproduce on Windows

Start the PostgreSQL service and create the root `.env` as described in the [project README](../../README.md). Then run from the repository root:

```powershell
Set-Location experiments/pdf-search
npm.cmd ci
npm.cmd test
npm.cmd run build
npm.cmd run dev
```

Open `http://127.0.0.1:5174`. Click the **Synthetic handbook, page 2** hit and confirm the rendered page contains “A helix appears on the second page.” Click **Synthetic image-only page — view only** to open the raster-only fixture. To try a different query, run `npm.cmd test -- catalyst` in this directory and refresh.

| Fixture | Verified result on Windows |
| --- | --- |
| Two-page handbook | Search for `helix` returns only page 2. |
| Two-column notes | `fractal` and `catalyst` both resolve to page 1. |
| Image-only page | Zero text indexed. The page remains viewable. |
| Absent keyword | Zero hits. |

The Vite build passed. Headless Chrome clicked the handbook hit, rendered text pixels on page 2, and opened the image-only page. The checks establish page mapping on this small corpus. Multi-column term matching does not establish reading order or phrase fidelity. OCR, malformed and encrypted inputs, exam authorization, and performance at realistic scale remain follow-up validation.
