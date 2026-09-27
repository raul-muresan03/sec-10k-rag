import { useEffect, useState } from 'react'
import { AnswerPanel } from '../components/AnswerPanel'
import { EvidencePanel } from '../components/EvidencePanel'
import { ExampleSelector } from '../components/ExampleSelector'
import { MetricsPanel } from '../components/MetricsPanel'
import { loadSnapshot } from '../data'
import type { Snapshot } from '../types'

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

  if (loading) return <div className="load-message" role="status">Loading saved evaluation data…</div>
  if (error || !snapshot || !selected) {
    return (
      <div className="load-message load-error" role="alert">
        <h2>Evaluation replay unavailable</h2>
        <p>{error ?? 'The evaluation data is incomplete.'}</p>
        <button type="button" className="button button-primary" onClick={() => setRetry(value => value + 1)}>
          Try again
        </button>
      </div>
    )
  }

  return (
    <>
      <MetricsPanel snapshot={snapshot} />
      <section className="explorer-section" id="evaluation-cases" aria-labelledby="explorer-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">02 / Saved replay — not live answers</p>
            <h2 id="explorer-heading">Look past the score.</h2>
          </div>
          <p className="section-caption">
            {snapshot.examples.length} selected dev cases · Successes, refusals and failures
          </p>
        </div>
        <div className="insight-banner">
          <span className="insight-symbol" aria-hidden="true">≠</span>
          <p><strong>A retrieval hit is not a correct answer.</strong> Ford’s gold passage was found in the
            saved context, yet the model answered the wrong fact.</p>
          <button type="button" onClick={() => setSelectedId('f-2014-numeric')}>
            Inspect Ford case →
          </button>
        </div>
        <div className="explorer-grid">
          <ExampleSelector examples={snapshot.examples} selected={selected} onSelect={setSelectedId} />
          <div className="case-content">
            <AnswerPanel example={selected} />
            <EvidencePanel example={selected} />
          </div>
        </div>
      </section>
      <section className="method-section" aria-labelledby="method-heading">
        <p className="eyebrow">03 / Read the fine print</p>
        <h2 id="method-heading">Two runs. Different claims.</h2>
        <div className="method-grid">
          <div><span className="method-number">01</span><h3>Answer run</h3>
            <p>Saved responses use {snapshot.runs.answers.generation_model_tag} with the top{' '}
              {snapshot.runs.answers.top_n} retrieved chunks. Reviews apply only to these exact
              responses.{' '}
              {pendingReviews > 0
                ? `${pendingReviews} judgments await owner confirmation.`
                : 'Owner checkpoints are complete.'}</p>
            <code>{snapshot.runs.answers.run_id}</code>
          </div>
          <div><span className="method-number">02</span><h3>Retrieval run</h3>
            <p>Retrieval metrics use an independent top-{snapshot.runs.retrieval.top_n} ranking, without
              generating answers. Model tags alone do not establish immutable model weights.</p>
            <code>{snapshot.runs.retrieval.run_id}</code>
          </div>
          <div><span className="method-number">03</span><h3>Held-out check</h3>
            <p>Metrics above use 24 dev questions. Another 16 test questions are reserved for a final
              check, rather than tuning this demo.</p>
            <a className="inline-link" href={REPORT_URL} target="_blank" rel="noopener noreferrer">
              Full methodology <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>
      </section>
    </>
  )
}
