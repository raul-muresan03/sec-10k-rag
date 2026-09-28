export interface FilingSummary {
  filing_id: string
  ticker: string
  company: string
  filing_year: number
  sec_url: string
  status: 'unprepared' | 'queued' | 'downloading' | 'waiting_for_models' | 'indexing' | 'ready' | 'failed'
  detail: string | null
}

export interface PreparationResult {
  status: FilingSummary['status']
  detail: string | null
}

const filingStatuses: FilingSummary['status'][] = [
  'unprepared', 'queued', 'downloading', 'waiting_for_models', 'indexing', 'ready', 'failed',
]

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

function errorMessage(status: number): string {
  if (status === 404) return 'This filing is no longer available. Choose another and try again.'
  if (status === 422) return 'Please enter a shorter question and try again.'
  if (status === 504) return 'This is taking longer than expected. Please try again.'
  return 'We couldn’t complete your request right now. Please try again.'
}

function isFiling(value: unknown): value is FilingSummary {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const filing = value as Record<string, unknown>
  return typeof filing.filing_id === 'string'
    && typeof filing.ticker === 'string'
    && typeof filing.company === 'string'
    && typeof filing.filing_year === 'number'
    && typeof filing.sec_url === 'string'
    && typeof filing.status === 'string' && filingStatuses.includes(filing.status as FilingSummary['status'])
    && (filing.detail === null || typeof filing.detail === 'string')
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
  if (!response.ok) throw new ApiError(response.status, errorMessage(response.status))
  const data: unknown = await response.json()
  if (!Array.isArray(data) || !data.every(isFiling)) {
    throw new ApiError(response.status, 'We couldn’t load the available filings. Please try again.')
  }
  if (data.length === 0) {
    throw new ApiError(response.status, 'No filings are available right now.')
  }
  return data
}

export async function prepareFiling(filingId: string): Promise<PreparationResult> {
  const response = await fetch(`/api/filings/${encodeURIComponent(filingId)}/prepare`, { method: 'POST' })
  if (!response.ok) throw new ApiError(response.status, errorMessage(response.status))
  const data: unknown = await response.json()
  if (data === null || typeof data !== 'object' || Array.isArray(data)) {
    throw new ApiError(response.status, 'We couldn’t open this filing. Please try again.')
  }
  const result = data as Record<string, unknown>
  if (typeof result.status !== 'string' || !filingStatuses.includes(result.status as FilingSummary['status'])
    || (result.detail !== null && typeof result.detail !== 'string')) {
    throw new ApiError(response.status, 'We couldn’t open this filing. Please try again.')
  }
  return result as unknown as PreparationResult
}

export async function postChat(filingId: string, question: string, signal: AbortSignal): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filing_id: filingId, question }),
    signal,
  })
  if (!response.ok) throw new ApiError(response.status, errorMessage(response.status))
  const data: unknown = await response.json()
  if (!isChat(data)) {
    throw new ApiError(response.status, 'We couldn’t complete your request right now. Please try again.')
  }
  if (data.filing_id !== filingId) {
    throw new ApiError(response.status, 'We couldn’t complete your request right now. Please try again.')
  }
  return data
}
