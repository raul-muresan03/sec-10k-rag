import type { Example, Review } from './types'

const companies: Record<string, string> = {
  ADBE: 'Adobe', AMZN: 'Amazon', F: 'Ford', NVDA: 'NVIDIA', PFE: 'Pfizer', SBUX: 'Starbucks',
}
const questionTypes: Record<string, string> = {
  numeric: 'Numeric', narrative: 'Narrative', multi_hop: 'Multi-hop', no_answer: 'No-answer',
}

export function companyName(ticker: string): string {
  return companies[ticker] ?? ticker
}

export function questionType(type: string): string {
  return questionTypes[type] ?? type
}

export function reviewLabel(review: Review): string {
  if (review.status === 'unreviewed') return 'Unreviewed'
  if (review.status === 'needs_owner_confirmation') return 'Owner confirmation pending'
  return review.status === 'owner_confirmed' ? 'Owner-confirmed' : 'AI-reviewed'
}

export function verdictLabel(review: Review): string {
  return review.verdict ?? 'Not assessed'
}

export function exampleLabel(example: Example): string {
  return `${companyName(example.ticker)} · ${example.filing_year} · ${questionType(example.question_type)}`
}
