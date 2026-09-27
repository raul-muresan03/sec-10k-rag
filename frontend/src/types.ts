export type Verdict = 'pass' | 'partial' | 'incorrect' | null
export type ReviewStatus = 'ai_reviewed' | 'needs_owner_confirmation' | 'owner_confirmed' | 'unreviewed'

export interface Review {
  status: ReviewStatus
  confidence: 'high' | 'medium' | 'low' | null
  verdict: Verdict
  dimensions: Record<string, string>
  explanation: string
}

export interface Example {
  id: string
  answer_run_id: string
  ticker: string
  filing_year: number
  question_type: string
  question: string
  generated_answer: string
  reference_answer: string | null
  reference_evidence: string[]
  reference_verification_note: string | null
  section: string | null
  answer_run_evidence_found: boolean[]
  review: Review
  sec_url: string
  accession: string
  retrieved_context: { rank: number; score: number; text: string }[]
}

export interface CountMetric {
  hits?: number
  complete?: number
  questions: number
  rate: number | null
}

export interface Snapshot {
  schema_version: number
  dataset: { split: string; questions: number; answerable: number; no_answer: number; filings: number }
  runs: {
    answers: { run_id: string; top_n: number; generation_model_tag: string; provenance_note: string }
    retrieval: { run_id: string; top_n: number; embedding_model: { tag: string } }
  }
  retrieval_metrics: {
    run_id: string
    method: string
    scope: string
    values: {
      hit_at_5: CountMetric
      hit_at_10: CountMetric
      multi_hop_all_evidence_at_5: CountMetric
      multi_hop_all_evidence_at_10: CountMetric
      mrr_at_10: { questions: number; rate: number | null }
    }
  }
  answer_review: {
    run_id: string
    assessment_source: string
    summary: {
      reviewed: number
      unreviewed: number
      pending_owner_confirmation: number
      owner_confirmed: number
      verdicts: { pass: number; partial: number; incorrect: number }
      publication_status: string
    }
  }
  examples: Example[]
}
