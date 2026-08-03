import { describe, expect, it, vi } from 'vitest'

import { ApiError, apiRequest, buildApiUrl, getJson } from '@/lib/api-client'

describe('cliente HTTP', () => {
  it('construye una URL desde la base configurada', () => {
    expect(buildApiUrl('/health', 'http://localhost:8000/')).toBe(
      'http://localhost:8000/health',
    )
  })

  it('serializa query params e ignora valores undefined', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify({ total: 2 })))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      getJson<{ total: number }>('/api/incidents?status=active', {
        query: { limit: 6, client: undefined, exact: true },
      }),
    ).resolves.toEqual({ total: 2 })

    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8000/api/incidents?status=active&limit=6&exact=true',
    )
  })

  it('propaga el AbortSignal a fetch', async () => {
    const controller = new AbortController()
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getJson('/health', { signal: controller.signal })).resolves.toBe(
      undefined,
    )
    expect(fetchMock.mock.calls[0][1]?.signal).toBe(controller.signal)
  })

  it('no incluye el cuerpo sensible de un error en el mensaje', async () => {
    const sensitiveBody = { detail: 'token-super-secreto' }
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(sensitiveBody), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const error = await getJson('/private').catch((reason: unknown) => reason)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 500, responseBody: sensitiveBody })
    expect((error as Error).message).not.toContain('token-super-secreto')
  })

  it('mantiene apiRequest sobre el parser JSON controlado', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify({ status: 'ok' })))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiRequest<{ status: string }>('/health')).resolves.toEqual({
      status: 'ok',
    })
  })
})
