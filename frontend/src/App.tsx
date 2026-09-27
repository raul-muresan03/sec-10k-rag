import { useEffect, useState } from 'react'
import { AnswerPanel } from './components/AnswerPanel'
import { EvidencePanel } from './components/EvidencePanel'
import { ExampleSelector } from './components/ExampleSelector'
import { MetricsPanel } from './components/MetricsPanel'
import { loadSnapshot } from './data'
import type { Snapshot } from './types'

const REPO_URL = 'https://github.com/raul-muresan03/sec-rag-tool'
const REPORT_URL = `${REPO_URL}/blob/main/eval/experiment_log.md`

function App() {
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

  return (
    <div className="site-shell">
      <header className="site-header container">
        <a className="brand" href="#top" aria-label="SEC RAG Evidence Lab home">
          <span className="brand-mark" aria-hidden="true">S<span>·</span>R</span>
          <span>SEC RAG <em>/</em> Evidence Lab</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#results">Results</a>
          <a href="#explorer">Case files</a>
          <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
            Source code <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <main id="top">
        <section className="hero container" aria-labelledby="hero-title">
          <div className="hero-copy">
            <div className="hero-kicker">
              <span className="live-dot" /> An open evaluation notebook <span>—</span> v1
            </div>
            <h1 id="hero-title">Evidence <i>before</i><br />answers.</h1>
            <p className="hero-description">
              Explore saved answers and retrieval evidence from a local SEC 10-K RAG pipeline. See where it works,
              where it misses, and why those are different questions.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#explorer">
                Explore the case files <span aria-hidden="true">↗</span>
              </a>
              <a className="button button-quiet" href={REPORT_URL} target="_blank" rel="noopener noreferrer">
                Read evaluation report <span aria-hidden="true">↗</span>
              </a>
            </div>
          </div>
          <aside className="hero-card" aria-label="How this demo works">
            <div className="card-topline"><span>DEMO / 001</span><span>SEC · 10-K</span></div>
            <div className="hero-card-icon" aria-hidden="true">
              <span>?</span><span>→</span><span>§</span><span>→</span><span>A</span>
            </div>
            <h2>Saved evaluation replay</h2>
            <p>Choose a question to inspect its generated answer, human-written reference and retrieved context.</p>
            <div className="card-divider" />
            <div className="card-foot"><span className="live-dot" /> No live inference · No arbitrary questions</div>
          </aside>
        </section>

        <div className="content-surface">
          <div className="container">
            {loading && <div className="load-message" role="status">Loading saved evaluation data…</div>}
            {!loading && error && (
              <div className="load-message load-error" role="alert">
                <h2>Evaluation data unavailable</h2>
                <p>{error}</p>
                <button type="button" className="button button-primary" onClick={() => setRetry(value => value + 1)}>
                  Try again
                </button>
              </div>
            )}
            {!loading && snapshot && !error && selected && (
              <>
                <MetricsPanel snapshot={snapshot} />
                <section className="explorer-section" id="explorer" aria-labelledby="explorer-heading">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">02 / Examine the record</p>
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
            )}
          </div>
        </div>
      </main>
      <footer className="site-footer container">
        <span>SEC RAG / Evidence Lab</span>
        <span>Built to make failure visible.</span>
        <a href={REPO_URL} target="_blank" rel="noopener noreferrer">View on GitHub ↗</a>
      </footer>
    </div>
  )
}

export default App
