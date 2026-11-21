import { afterEach, describe, expect, it, vi } from 'vitest'
import { checkBackend } from './health'

afterEach(() => vi.unstubAllGlobals())

describe('checkBackend', () => {
  it.each([
    [200, { status: 'ok', database: 'available' }, 'connected'],
    [503, { status: 'degraded', database: 'unavailable' }, 'degraded'],
    [503, { status: 'upstream error' }, 'unreachable'],
    [200, null, 'unreachable'],
  ])('maps HTTP %i and %j to %s', async (status, body, expected) => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json(body, { status }))
    vi.stubGlobal('fetch', fetchMock)
    const { signal } = new AbortController()

    expect(await checkBackend(signal)).toBe(expected)
    expect(fetchMock).toHaveBeenCalledWith('/api/health', { signal, cache: 'no-store' })
  })

  it('reports a failed request as unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Connection failed')))

    expect(await checkBackend(new AbortController().signal)).toBe('unreachable')
  })
})
