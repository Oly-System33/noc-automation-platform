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

export type RequestJsonOptions = {
  body?: unknown
  method?: string
  signal?: AbortSignal
  query?: Record<string, QueryValue>
}

export type GetJsonOptions = Omit<RequestJsonOptions, 'body' | 'method'>
export type PostJsonOptions = Omit<RequestJsonOptions, 'method' | 'query'>

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

export async function requestJson<T>(
  path: string,
  { body, method = 'GET', signal, query }: RequestJsonOptions = {},
): Promise<T> {
  const url = new URL(buildApiUrl(path))

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) {
      url.searchParams.append(key, String(value))
    }
  }

  const response = await fetch(url.toString(), {
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    method,
    signal,
  })
  return parseJsonResponse<T>(response)
}

export function getJson<T>(path: string, options: GetJsonOptions = {}) {
  return requestJson<T>(path, options)
}

export function postJson<T>(path: string, options: PostJsonOptions = {}) {
  return requestJson<T>(path, { ...options, method: 'POST' })
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(buildApiUrl(path), options)
  return parseJsonResponse<T>(response)
}
