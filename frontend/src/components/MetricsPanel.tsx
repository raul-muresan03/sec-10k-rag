import type { Snapshot } from '../types'
import { eyebrow, sectionCaption, sectionHeading, sectionTitle } from '../ui'

interface Props {
  snapshot: Snapshot
}

export function MetricsPanel({ snapshot }: Props) {
  const { dataset, retrieval_metrics: retrieval, answer_review: reviews } = snapshot
  const values = retrieval.values
  const multiHopAtFive = values.multi_hop_all_evidence_at_5
  const multiHopAtTen = values.multi_hop_all_evidence_at_10

  return (
    <section className="metrics-section" aria-labelledby="metrics-heading" id="results">
      <div className={sectionHeading}>
        <div>
          <p className={`${eyebrow} mb-2`}>01 / Measured behavior</p>
          <h2 id="metrics-heading" className={sectionTitle}>What the evaluation found</h2>
        </div>
        <p className={sectionCaption}>
          {dataset.questions} dev questions · {dataset.answerable} answerable · {dataset.no_answer} no-answer ·{' '}
          {dataset.filings} filings
        </p>
      </div>

      <div className="metric-grid" aria-label="Strict retrieval metrics">
        <Metric value={`${values.hit_at_5.hits}/${values.hit_at_5.questions}`} label="Evidence hit @ 5"
          detail="At least one gold quote found" />
        <Metric value={`${values.hit_at_10.hits}/${values.hit_at_10.questions}`} label="Evidence hit @ 10"
          detail="Answerable dev questions" featured />
        <Metric value={values.mrr_at_10.rate?.toFixed(3) ?? 'N/A'} label="MRR @ 10"
          detail="First strict matching rank" />
        <Metric value={`${multiHopAtTen.complete}/${multiHopAtTen.questions}`} label="All evidence @ 10"
          detail={`Multi-hop · ${multiHopAtFive.complete}/${multiHopAtFive.questions} at rank 5`} />
      </div>

      <div className="results-note">
        <span className="note-icon" aria-hidden="true">i</span>
        <p>
          These numbers come from a <strong>retrieval-only top-10 run</strong>. Strict quote matching measures whether
          evidence appeared in retrieved text; it does <strong>not</strong> score answer correctness. Equivalent table
          evidence can be missed by the exact-text proxy.
        </p>
      </div>

      <div className="review-summary">
        <div>
            <p className={`${eyebrow} mb-[5px]`}>Separate answer review · top 5</p>
          <h3>Generated answers need their own assessment.</h3>
          <p>
            AI-assisted review of {reviews.summary.reviewed} saved answers: {reviews.summary.verdicts.pass} pass,{' '}
            {reviews.summary.verdicts.partial} partial, {reviews.summary.verdicts.incorrect} incorrect.
            {reviews.summary.unreviewed > 0 && ` ${reviews.summary.unreviewed} unreviewed.`}
          </p>
        </div>
        <span className="status-pill pending">
          {reviews.summary.pending_owner_confirmation > 0
            ? `Provisional · ${reviews.summary.pending_owner_confirmation} awaiting owner review`
            : reviews.summary.publication_status === 'owner_checkpoint_complete'
              ? 'Owner checkpoints complete' : 'Provisional'}
        </span>
      </div>
    </section>
  )
}

function Metric({ value, label, detail, featured = false }: {
  value: string; label: string; detail: string; featured?: boolean
}) {
  return (
    <div className={`metric-card${featured ? ' featured' : ''}`}>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
      <span className="metric-detail">{detail}</span>
    </div>
  )
}
