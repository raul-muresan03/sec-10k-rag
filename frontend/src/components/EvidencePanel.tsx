import { useState } from 'react'
import type { Example } from '../types'

interface Props {
  example: Example
}

export function EvidencePanel({ example }: Props) {
  const [unwrappedChunk, setUnwrappedChunk] = useState<string | null>(null)

  return (
    <section className="evidence-panel" aria-labelledby="evidence-heading">
      <div className="evidence-header">
        <div>
          <p className="eyebrow">Trace the evidence</p>
          <h3 id="evidence-heading">What did the system see?</h3>
        </div>
        <a href={example.sec_url} target="_blank" rel="noopener noreferrer" className="inline-link">
          SEC filing <span aria-hidden="true">↗</span>
        </a>
      </div>

      <div className="gold-evidence">
        <div className="evidence-label-row">
          <h4>Gold reference evidence</h4>
          <span>Quoted passages from the evaluation set</span>
        </div>
        {example.reference_evidence.length ? (
          <ol>
            {example.reference_evidence.map((quote, index) => (
              <li key={index}>
                <blockquote>{quote}</blockquote>
                <span className={example.answer_run_evidence_found[index]
                  ? 'match-label found' : 'match-label missing'}>
                  {example.answer_run_evidence_found[index]
                    ? 'Strict match in saved top 5' : 'No strict match in saved top 5'}
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty-evidence">Not applicable — no gold passage is assigned to this no-answer question.</p>
        )}
      </div>

      <div className="retrieved-heading">
        <div>
          <h4>Retrieved context</h4>
          <p>Complete saved top-five chunks from the answer run, in original rank order.</p>
        </div>
        <span className="rank-count">01—05</span>
      </div>
      <div className="chunk-list">
        {example.retrieved_context.map(chunk => {
          const chunkId = `${example.id}-${chunk.rank}`
          const hasTable = /\|\s*-{3,}/.test(chunk.text)
          return <details key={chunkId} className="chunk" open={chunk.rank === 1}>
            <summary>
              <span className="chunk-rank">R{chunk.rank}</span>
              <span>Retrieved passage <span className="chunk-preview">· {chunk.text.slice(0, 65)}…</span></span>
              <span className="chunk-score">Similarity {chunk.score.toFixed(3)}</span>
            </summary>
            {hasTable && <div className="chunk-view-options">
              <button type="button" aria-pressed={unwrappedChunk === chunkId}
                onClick={() => setUnwrappedChunk(unwrappedChunk === chunkId ? null : chunkId)}>
                {unwrappedChunk === chunkId ? 'Wrap long lines' : 'Preserve table rows ↔'}
              </button>
            </div>}
            <div className="chunk-viewport">
              {unwrappedChunk === chunkId
                ? <TableAwareText text={chunk.text} />
                : <pre className="chunk-text">{chunk.text}</pre>}
            </div>
          </details>
        })}
      </div>
      <p className="evidence-footnote">
        The SEC link opens the full submission, not a precise passage citation. A missing strict quote can still have
        equivalent table evidence; inspect the actual context before diagnosing retrieval.
      </p>
    </section>
  )
}

function TableAwareText({ text }: { text: string }) {
  return <div className="chunk-text table-layout">
    {text.split('\n').map((line, index) => {
      const first = line.indexOf('|')
      const last = line.lastIndexOf('|')
      return <div className="source-line" key={index}>
        {first >= 0 && last > first ? <>
          {line.slice(0, first) && <span>{line.slice(0, first)}</span>}
          <span className="source-table-row">{line.slice(first, last + 1)}</span>
          {line.slice(last + 1) && <span>{line.slice(last + 1)}</span>}
        </> : (line || '\u00a0')}
      </div>
    })}
  </div>
}
