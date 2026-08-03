import { describe, expect, it } from 'vitest'

import { readEnv } from '@/config/env'

describe('readEnv', () => {
  it('aplica valores locales predeterminados', () => {
    expect(readEnv({})).toEqual({
      apiBaseUrl: 'http://localhost:8000',
      pollIntervalMs: 15_000,
    })
  })

  it('transforma el intervalo configurado a número', () => {
    expect(readEnv({ VITE_POLL_INTERVAL_MS: '30000' }).pollIntervalMs).toBe(
      30_000,
    )
  })

  it.each(['invalido', '0', '-10'])(
    'usa un valor seguro para el intervalo %s',
    (value) => {
      expect(readEnv({ VITE_POLL_INTERVAL_MS: value }).pollIntervalMs).toBe(
        15_000,
      )
    },
  )
})
