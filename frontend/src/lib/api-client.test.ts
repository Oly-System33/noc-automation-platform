import { describe, expect, it, vi } from 'vitest'

import { ApiError, apiRequest, buildApiUrl } from '@/lib/api-client'

describe('cliente HTTP', () => {
  it('construye una URL desde la base configurada', () => {
    expect(buildApiUrl('/health', 'http://localhost:8000/')).toBe(
      'http://localhost:8000/health',
    )
  })

  it('genera un error controlado ante una respuesta no exitosa', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
    } as Response)
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiRequest('/health')).rejects.toEqual(new ApiError(503))
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})
