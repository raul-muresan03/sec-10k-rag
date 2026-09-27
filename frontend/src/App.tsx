import { useState } from 'react'
import { ChatView } from './components/ChatView'
import { EvaluationView } from './views/EvaluationView'

const REPO_URL = 'https://github.com/raul-muresan03/sec-rag-tool'

type View = 'chat' | 'evaluation'

function App() {
  const [view, setView] = useState<View>('chat')

  const select = (next: View) => (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    setView(next)
  }

  return (
    <div className="site-shell">
      <header className="site-header container">
        <a className="brand" href="#top" aria-label="SEC RAG Evidence Lab home">
          <span className="brand-mark" aria-hidden="true">S<span>·</span>R</span>
          <span>SEC RAG <em>/</em> Evidence Lab</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#chat" aria-current={view === 'chat' ? 'page' : undefined} onClick={select('chat')}>Chat</a>
          <a
            href="#evaluation"
            aria-current={view === 'evaluation' ? 'page' : undefined}
            onClick={select('evaluation')}
          >
            Evaluation
          </a>
          <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
            Source code <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <main id="top">
        <section className="hero container" aria-labelledby="hero-title">
          <div className="hero-copy">
            <div className="hero-kicker">
              <span className="live-dot" /> Live answers over verified 10-K filings <span>—</span> v1
            </div>
            <h1 id="hero-title">Evidence <i>before</i><br />answers.</h1>
            <p className="hero-description">
              Ask a question about one verified filing and read the generated answer next to the
              retrieved passages. The saved evaluation replay lives under Evaluation.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#chat" onClick={select('chat')}>
                Ask a question <span aria-hidden="true">↗</span>
              </a>
              <a className="button button-quiet" href="#evaluation" onClick={select('evaluation')}>
                Inspect saved evaluation <span aria-hidden="true">↗</span>
              </a>
            </div>
          </div>
          <aside className="hero-card" aria-label="How this app works">
            <div className="card-topline"><span>LIVE / 001</span><span>SEC · 10-K</span></div>
            <div className="hero-card-icon" aria-hidden="true">
              <span>?</span><span>→</span><span>§</span><span>→</span><span>A</span>
            </div>
            <h2>Live filing chat</h2>
            <p>Choose a filing, ask in your own words, and inspect the answer with its evidence.</p>
            <div className="card-divider" />
            <div className="card-foot"><span className="live-dot" /> Live inference · Independent questions</div>
          </aside>
        </section>

        <div className="content-surface">
          <div className="container">
            {view === 'chat' ? (
              <ChatView />
            ) : (
              <EvaluationView />
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
