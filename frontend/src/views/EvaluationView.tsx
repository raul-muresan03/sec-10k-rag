import { useEffect, useState } from 'react'
import { AnswerPanel } from '../components/AnswerPanel'
import { EvidencePanel } from '../components/EvidencePanel'
import { ExampleSelector } from '../components/ExampleSelector'
import { MetricsPanel } from '../components/MetricsPanel'
import { loadSnapshot } from '../data'
import type { Snapshot } from '../types'
import {
  caseContent, eyebrow, explorerGrid, inlineLink, loadErrorTitle, loadMessage, primaryButton,
  sectionCaption, sectionHeading, sectionTitle,
} from '../ui'

const REPO_URL = 'https://github.com/raul-muresan03/sec-rag-tool'
const REPORT_URL = `${REPO_URL}/blob/main/eval/experiment_log.md`

export function EvaluationView() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    loadSnapshot(controller.signal)
      .then(data => {
        if (!controller.signal.aborted) setSnapshot(data)
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to load data.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [retry])

  const selected = snapshot?.examples.find(example => example.id === selectedId) ?? snapshot?.examples[0]
  const pendingReviews = snapshot?.answer_review.summary.pending_owner_confirmation ?? 0

  if (loading) return <div className={loadMessage} role="status">Loading saved evaluation data…</div>
  if (error || !snapshot || !selected) {
    return (
      <div className={loadMessage} role="alert">
        <h2 className={loadErrorTitle}>Evaluation replay unavailable</h2>
        <p>{error ?? 'The evaluation data is incomplete.'}</p>
        <button type="button" className={`${primaryButton} mt-[10px]`}
          onClick={() => setRetry(value => value + 1)}>
          Try again
        </button>
      </div>
    )
  }

  return (
    <>
      <MetricsPanel snapshot={snapshot} />
      <section className="pt-[78px] pb-[90px]" id="evaluation-cases"
        aria-labelledby="explorer-heading">
        <div className={sectionHeading}>
          <div>
            <p className={`${eyebrow} mb-2`}>02 / Saved replay — not live answers</p>
            <h2 id="explorer-heading" className={sectionTitle}>Look past the score.</h2>
          </div>
          <p className={sectionCaption}>
            {snapshot.examples.length} selected dev cases · Successes, refusals and failures
          </p>
        </div>
        <div className="mb-5 flex items-center gap-5 rounded border border-[#c9d6cb] bg-[#e6eee6]
          px-6 py-[18px]">
          <span className="font-display text-[2.4rem] leading-none text-[#357b65]" aria-hidden="true">≠</span>
          <p className="m-0 flex-1 text-[.8rem] leading-[1.6] text-[#385450]">
            <strong>A retrieval hit is not a correct answer.</strong> Ford’s gold passage was found in the
            saved context, yet the model answered the wrong fact.</p>
          <button type="button" className="shrink-0 border-0 bg-transparent text-[.77rem]
            font-extrabold text-[#205f50] underline underline-offset-4"
            onClick={() => setSelectedId('f-2014-numeric')}>
            Inspect Ford case →
          </button>
        </div>
        <div className={explorerGrid}>
          <ExampleSelector examples={snapshot.examples} selected={selected} onSelect={setSelectedId} />
          <div className={caseContent}>
            <AnswerPanel example={selected} />
            <EvidencePanel example={selected} />
          </div>
        </div>
      </section>
      <section className="border-t border-[#d8deda] pt-[76px] pb-[88px]"
        aria-labelledby="method-heading">
        <p className={`${eyebrow} mb-3`}>03 / Read the fine print</p>
        <h2 id="method-heading" className={sectionTitle}>Two runs. Different claims.</h2>
        <div className="mt-[35px] grid grid-cols-3 gap-[38px]">
          <div className="min-w-0 border-t border-[#bfc9c5] pt-[19px]">
            <span className="font-code text-[.73rem] text-[#629082]">01</span>
            <h3 className="my-3 font-display text-[1.3rem] font-normal">Answer run</h3>
            <p className="text-[.8rem] leading-[1.7] text-[#5e6a70]">
              Saved responses use {snapshot.runs.answers.generation_model_tag} with the top{' '}
              {snapshot.runs.answers.top_n} retrieved chunks. Reviews apply only to these exact
              responses.{' '}
              {pendingReviews > 0
                ? `${pendingReviews} judgments await owner confirmation.`
                : 'Owner checkpoints are complete.'}</p>
            <code className="block text-[.66rem] text-[#52676a] [overflow-wrap:anywhere]">
              {snapshot.runs.answers.run_id}
            </code>
          </div>
          <div className="min-w-0 border-t border-[#bfc9c5] pt-[19px]">
            <span className="font-code text-[.73rem] text-[#629082]">02</span>
            <h3 className="my-3 font-display text-[1.3rem] font-normal">Retrieval run</h3>
            <p className="text-[.8rem] leading-[1.7] text-[#5e6a70]">
              Retrieval metrics use an independent top-{snapshot.runs.retrieval.top_n} ranking, without
              generating answers. Model tags alone do not establish immutable model weights.</p>
            <code className="block text-[.66rem] text-[#52676a] [overflow-wrap:anywhere]">
              {snapshot.runs.retrieval.run_id}
            </code>
          </div>
          <div className="min-w-0 border-t border-[#bfc9c5] pt-[19px]">
            <span className="font-code text-[.73rem] text-[#629082]">03</span>
            <h3 className="my-3 font-display text-[1.3rem] font-normal">Held-out check</h3>
            <p className="text-[.8rem] leading-[1.7] text-[#5e6a70]">
              Metrics above use 24 dev questions. Another 16 test questions are reserved for a final
              check, rather than tuning this demo.</p>
            <a className={inlineLink} href={REPORT_URL} target="_blank" rel="noopener noreferrer">
              Full methodology <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>
      </section>
    </>
  )
}
