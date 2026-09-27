import { useState } from 'react'
import { FilingSelector } from './FilingSelector'

export function ChatView() {
  const [filingId, setFilingId] = useState<string | null>(null)

  return (
    <section aria-labelledby="chat-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">01 / Live filing chat</p>
          <h2 id="chat-heading">Ask a verified filing.</h2>
        </div>
        <p className="section-caption">
          Each question is independent. Refreshing the page clears these messages.
        </p>
      </div>
      <div className="explorer-grid">
        <FilingSelector selectedId={filingId} disabled={false} onSelect={setFilingId} />
        <div className="load-message" role="status">
          <p>
            {filingId === null
              ? 'Loading the verified filing catalog…'
              : 'The question form arrives in the next change.'}
          </p>
        </div>
      </div>
    </section>
  )
}
