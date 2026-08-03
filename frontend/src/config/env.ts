const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const DEFAULT_POLL_INTERVAL_MS = 15_000

type EnvironmentSource = {
  VITE_API_BASE_URL?: string
  VITE_POLL_INTERVAL_MS?: string
}

export type AppConfig = {
  apiBaseUrl: string
  pollIntervalMs: number
}

export function readEnv(source: EnvironmentSource): AppConfig {
  const configuredInterval = Number(source.VITE_POLL_INTERVAL_MS)
  const pollIntervalMs =
    Number.isFinite(configuredInterval) && configuredInterval > 0
      ? configuredInterval
      : DEFAULT_POLL_INTERVAL_MS

  return {
    apiBaseUrl: source.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL,
    pollIntervalMs,
  }
}

export const env = readEnv({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_POLL_INTERVAL_MS: import.meta.env.VITE_POLL_INTERVAL_MS,
})
