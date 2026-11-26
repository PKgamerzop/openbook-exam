import type { SVGProps } from 'react'

const paths = {
  book: 'M12 6v15M3 4h4a5 5 0 0 1 5 2 5 5 0 0 1 5-2h4v15h-4a5 5 0 0 0-5 2 5 5 0 0 0-5-2H3z',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  clock: 'M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
  check: 'm5 12 4 4L19 6',
  flag: 'M5 22V3m0 1c5-4 9 4 15 0v11c-6 4-10-4-15 0',
  left: 'm15 5-7 7 7 7',
  right: 'm9 5 7 7-7 7',
  search: 'M15 15l5 5m-3-9a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z',
  bookmark: 'M6 3h12v18l-6-4-6 4z',
  file: 'M5 3h9l5 5v13H5zM14 3v6h5M8 13h8m-8 4h8',
  calculator: 'M5 2h14v20H5zM8 6h8M8 11h1m6 0h1m-8 4h1m6 0h1m-8 4h1m6 0h1',
  edit: 'm14 5 5 5M4 20l1-6L16 3l5 5L10 19z',
  expand: 'M9 3H3v6m12-6h6v6M3 15v6h6m12-6v6h-6',
  shrink: 'M3 9h6V3m12 6h-6V3M9 21v-6H3m12 6v-6h6',
  minus: 'M5 12h14',
  plus: 'M5 12h14m-7-7v14',
  logout: 'M10 3H4v18h6m4-5 4-4-4-4m-6 4h12',
  refresh: 'M20 7v5h-5m5 0a8 8 0 1 0-2 5',
  close: 'm6 6 12 12M18 6 6 18',
}

export function Icon({ name, ...props }: SVGProps<SVGSVGElement> & {
  name: keyof typeof paths
}) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
      strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <path d={paths[name]} />
    </svg>
  )
}
