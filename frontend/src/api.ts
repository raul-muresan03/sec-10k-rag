export interface FilingSummary {
  filing_id: string
  ticker: string
  company: string
  filing_year: number
  sec_url: string
}

export interface RetrievedChunk {
  rank: number
  score: number
  text: string
}

export interface StageTimes {
  retrieval: number
  generation: number
  total: number
}

export interface ChatResponse {
  answer: string
  filing_id: string
  model: string
  retrieved_chunks: RetrievedChunk[]
  sec_url: string
  stage_times_seconds: StageTimes
  request_id: string
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function readDetail(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json()
    if (data !== null && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: unknown }).detail
      if (typeof detail === 'string' && detail.trim()) return detail
    }
  } catch {
    // Fall through to a status-based message below.
  }
  if (response.status === 404) return 'Unknown filing. Pick another filing and try again.'
  if (response.status === 422) return 'Type a question between 1 and 2000 characters.'
  if (response.status === 502) return 'The model service returned an invalid response.'
  if (response.status === 503) return 'The service is unavailable. Try again shortly.'
  if (response.status === 504) return 'The request timed out. Try a shorter question.'
  return `The request failed (HTTP ${response.status}).`
}

function isFiling(value: unknown): value is FilingSummary {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const filing = value as Record<string, unknown>
  return typeof filing.filing_id === 'string'
    && typeof filing.ticker === 'string'
    && typeof filing.company === 'string'
    && typeof filing.filing_year === 'number'
    && typeof filing.sec_url === 'string'
}

function isStageTimes(value: unknown): value is StageTimes {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const times = value as Record<string, unknown>
  return ['retrieval', 'generation', 'total'].every(stage =>
    typeof times[stage] === 'number' && Number.isFinite(times[stage]) && times[stage] >= 0,
  )
}

function isChat(value: unknown): value is ChatResponse {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const chat = value as Record<string, unknown>
  return typeof chat.answer === 'string'
    && typeof chat.filing_id === 'string'
    && typeof chat.model === 'string'
    && Array.isArray(chat.retrieved_chunks)
    && (chat.retrieved_chunks as unknown[]).every(chunk =>
      chunk !== null && typeof chunk === 'object' && !Array.isArray(chunk)
      && typeof (chunk as { rank: unknown }).rank === 'number'
      && typeof (chunk as { score: unknown }).score === 'number'
      && typeof (chunk as { text: unknown }).text === 'string')
    && typeof chat.sec_url === 'string'
    && typeof chat.request_id === 'string'
    && isStageTimes(chat.stage_times_seconds)
}

export async function fetchFilings(signal: AbortSignal): Promise<FilingSummary[]> {
  const response = await fetch('/api/filings', { signal })
  if (!response.ok) throw new ApiError(response.status, await readDetail(response))
  const data: unknown = await response.json()
  if (!Array.isArray(data) || !data.every(isFiling)) {
    throw new ApiError(response.status, 'The filing catalog is incomplete or uses an unsupported format.')
  }
  if (data.length === 0) {
    throw new ApiError(response.status, 'No verified filings are prepared yet. Prepare the dev indexes and try again.')
  }
  return data
}

export async function postChat(filingId: string, question: string, signal: AbortSignal): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filing_id: filingId, question }),
    signal,
  })
  if (!response.ok) throw new ApiError(response.status, await readDetail(response))
  const data: unknown = await response.json()
  if (!isChat(data)) {
    throw new ApiError(response.status, 'The answer is incomplete or uses an unsupported format.')
  }
  if (data.filing_id !== filingId) {
    throw new ApiError(response.status, 'The answer belongs to a different filing. Please try again.')
  }
  return data
}
