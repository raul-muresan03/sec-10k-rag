import type { Snapshot } from './types'

export async function loadSnapshot(signal: AbortSignal): Promise<Snapshot> {
  const response = await fetch(`${import.meta.env.BASE_URL}demo.v1.json`, { signal })
  if (!response.ok) {
    throw new Error(`The evaluation data could not be loaded (HTTP ${response.status}).`)
  }
  const data: unknown = await response.json()
  if (!isSnapshot(data)) {
    throw new Error('The evaluation data is incomplete or uses an unsupported format.')
  }
  return data
}

function isSnapshot(data: unknown): data is Snapshot {
  if (!isRecord(data)) return false
  const snapshot = data as Partial<Snapshot>
  return snapshot.schema_version === 1
    && snapshot.dataset?.split === 'dev'
    && typeof snapshot.dataset.questions === 'number'
    && Array.isArray(snapshot.examples)
    && snapshot.examples.length > 0
    && snapshot.examples.every(isExample)
    && typeof snapshot.runs?.answers?.run_id === 'string'
    && typeof snapshot.runs?.answers?.generation_model_tag === 'string'
    && typeof snapshot.runs?.retrieval?.run_id === 'string'
    && typeof snapshot.retrieval_metrics?.values?.hit_at_10?.questions === 'number'
    && typeof snapshot.retrieval_metrics.values.hit_at_5?.hits === 'number'
    && typeof snapshot.retrieval_metrics.values.mrr_at_10?.rate === 'number'
    && typeof snapshot.retrieval_metrics.values.multi_hop_all_evidence_at_10?.complete === 'number'
    && typeof snapshot.answer_review?.summary?.reviewed === 'number'
    && typeof snapshot.answer_review.summary.verdicts?.pass === 'number'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isExample(value: unknown): boolean {
  if (!isRecord(value) || !isRecord(value.review)) return false
  return typeof value.id === 'string' && typeof value.question === 'string'
    && typeof value.generated_answer === 'string'
    && (typeof value.reference_answer === 'string' || value.reference_answer === null)
    && Array.isArray(value.reference_evidence)
    && Array.isArray(value.answer_run_evidence_found)
    && Array.isArray(value.retrieved_context)
    && value.retrieved_context.every(chunk => isRecord(chunk)
      && typeof chunk.text === 'string' && typeof chunk.rank === 'number'
      && typeof chunk.score === 'number')
    && typeof value.review.status === 'string'
    && typeof value.review.explanation === 'string'
    && isRecord(value.review.dimensions)
    && typeof value.sec_url === 'string'
    && value.sec_url.startsWith('https://www.sec.gov/Archives/')
}
