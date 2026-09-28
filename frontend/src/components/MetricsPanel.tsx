import type { Snapshot } from '../types'
import { badge, eyebrow, sectionCaption, sectionHeading, sectionTitle } from '../ui'

interface Props {
  snapshot: Snapshot
}

export function MetricsPanel({ snapshot }: Props) {
  const { dataset, retrieval_metrics: retrieval, answer_review: reviews } = snapshot
  const values = retrieval.values
  const multiHopAtFive = values.multi_hop_all_evidence_at_5
  const multiHopAtTen = values.multi_hop_all_evidence_at_10

  return (
    <section className="border-b border-[#d8deda] pt-[75px] pb-[82px] max-[760px]:py-[60px]"
      aria-labelledby="metrics-heading" id="results">
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

      <div className="grid grid-cols-4 gap-3 max-[760px]:grid-cols-2 max-[460px]:gap-2"
        aria-label="Strict retrieval metrics">
        <Metric value={`${values.hit_at_5.hits}/${values.hit_at_5.questions}`} label="Evidence hit @ 5"
          detail="At least one gold quote found" />
        <Metric value={`${values.hit_at_10.hits}/${values.hit_at_10.questions}`} label="Evidence hit @ 10"
          detail="Answerable dev questions" featured />
        <Metric value={values.mrr_at_10.rate?.toFixed(3) ?? 'N/A'} label="MRR @ 10"
          detail="First strict matching rank" />
        <Metric value={`${multiHopAtTen.complete}/${multiHopAtTen.questions}`} label="All evidence @ 10"
          detail={`Multi-hop · ${multiHopAtFive.complete}/${multiHopAtFive.questions} at rank 5`} />
      </div>

      <div className="mt-[18px] flex items-start gap-[14px] text-[.81rem] leading-[1.65] text-[#55636b]">
        <span className="grid size-[21px] shrink-0 place-items-center rounded-full border border-[#7e9c98]
          font-display italic text-[#357769]" aria-hidden="true">i</span>
        <p className="m-0">
          These numbers come from a <strong>retrieval-only top-10 run</strong>. Strict quote matching measures whether
          evidence appeared in retrieved text; it does <strong>not</strong> score answer correctness. Equivalent table
          evidence can be missed by the exact-text proxy.
        </p>
      </div>

      <div className="mt-8 flex items-center justify-between gap-[26px] border-l-[3px] border-[#8caf9f]
        bg-[#ebece6] px-[30px] py-[25px] max-[760px]:flex-col max-[760px]:items-start
        max-[460px]:p-[19px]">
        <div>
            <p className={`${eyebrow} mb-[5px]`}>Separate answer review · top 5</p>
          <h3 className="mb-[7px] font-display text-[1.3rem] font-normal">
            Generated answers need their own assessment.
          </h3>
          <p className="m-0 text-[.82rem] leading-[1.6] text-[#58686c]">
            AI-assisted review of {reviews.summary.reviewed} saved answers: {reviews.summary.verdicts.pass} pass,{' '}
            {reviews.summary.verdicts.partial} partial, {reviews.summary.verdicts.incorrect} incorrect.
            {reviews.summary.unreviewed > 0 && ` ${reviews.summary.unreviewed} unreviewed.`}
          </p>
        </div>
        <span className={`${badge} bg-[#fcf0d9] text-[#845924]`}>
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
    <div className={`flex min-h-[184px] flex-col items-start rounded-[5px] border border-[#dee3df]
      bg-white p-6 max-[1000px]:p-5 max-[460px]:min-h-[150px] max-[460px]:p-[15px]
      ${featured ? 'border-[#c8dfd3] bg-[#e9f2ed]' : ''}`}>
      <span className="text-[.77rem] font-bold text-[#5a696d] max-[460px]:text-[.67rem]">{label}</span>
      <strong className="mt-[17px] font-display text-[clamp(2.35rem,4vw,3.5rem)] font-normal
        tracking-[-.055em] max-[460px]:text-[2.3rem]">{value}</strong>
      <span className="mt-auto pt-3 text-[.72rem] text-[#68777a] max-[460px]:text-[.67rem]">{detail}</span>
    </div>
  )
}
