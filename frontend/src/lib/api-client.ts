import { env } from '@/config/env'

export class ApiError extends Error {
  readonly status: number
  readonly responseBody: unknown

  constructor(status: number, responseBody?: unknown) {
    super(`La solicitud falló con estado HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.responseBody = responseBody
  }
}

type QueryValue = string | number | boolean | undefined

type GetJsonOptions = {
  signal?: AbortSignal
  query?: Record<string, QueryValue>
}

export function buildApiUrl(path: string, baseUrl = env.apiBaseUrl) {
  const normalizedBaseUrl = `${baseUrl.replace(/\/+$/, '')}/`
  const normalizedPath = path.replace(/^\/+/, '')

  return new URL(normalizedPath, normalizedBaseUrl).toString()
}

async function parseResponseBody(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T
  }

  if (!response.ok) {
    const responseBody = await parseResponseBody(response)
    throw new ApiError(response.status, responseBody)
  }

  return (await response.json()) as T
}

export async function getJson<T>(
  path: string,
  { signal, query }: GetJsonOptions = {},
): Promise<T> {
  const url = new URL(buildApiUrl(path))

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) {
      url.searchParams.append(key, String(value))
    }
  }

  const response = await fetch(url.toString(), { signal })
  return parseJsonResponse<T>(response)
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(buildApiUrl(path), options)
  return parseJsonResponse<T>(response)
}
