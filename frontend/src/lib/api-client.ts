import { env } from '@/config/env'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number) {
    super(`La solicitud falló con estado HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
  }
}

export function buildApiUrl(path: string, baseUrl = env.apiBaseUrl) {
  const normalizedBaseUrl = `${baseUrl.replace(/\/+$/, '')}/`
  const normalizedPath = path.replace(/^\/+/, '')

  return new URL(normalizedPath, normalizedBaseUrl).toString()
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(buildApiUrl(path), options)

  if (!response.ok) {
    throw new ApiError(response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
