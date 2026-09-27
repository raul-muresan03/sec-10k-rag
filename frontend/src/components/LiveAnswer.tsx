import { useState } from 'react'
import { ChunkText } from './ChunkText'
import type { ChatResponse } from '../api'

interface Props {
  answer: ChatResponse
}

export function LiveAnswer({ answer }: Props) {
  const [unwrappedChunk, setUnwrappedChunk] = useState<number | null>(null)
  const times = answer.stage_times_seconds

  return (
    <>
      <p className="answer-text">{answer.answer}</p>
      <p className="selector-context">
        Filing ID: {answer.filing_id}
        {' · '}{answer.model} · retrieval {times.retrieval.toFixed(2)}s
        {' · '}generation {times.generation.toFixed(2)}s
        {' · '}total {times.total.toFixed(2)}s
        {' · '}Request ID: {answer.request_id}
        {' · '}<a className="inline-link" href={answer.sec_url} target="_blank" rel="noopener noreferrer">
          SEC filing ↗
        </a>
      </p>
      <div className="retrieved-heading">
        <div>
          <h4>Retrieved context</h4>
          <p>Live top chunks from this filing, in rank order.</p>
        </div>
        <span className="rank-count">{String(answer.retrieved_chunks.length).padStart(2, '0')}</span>
      </div>
      <div className="chunk-list">
        {answer.retrieved_chunks.map(chunk => {
          const hasTable = /\|\s*-{3,}/.test(chunk.text)
          return <details key={chunk.rank} className="chunk" open={chunk.rank === 1}>
            <summary>
              <span className="chunk-rank">R{chunk.rank}</span>
              <span>Retrieved passage <span className="chunk-preview">· {chunk.text.slice(0, 65)}…</span></span>
              <span className="chunk-score">Similarity {chunk.score.toFixed(3)}</span>
            </summary>
            {hasTable && <div className="chunk-view-options">
              <button type="button" aria-pressed={unwrappedChunk === chunk.rank}
                onClick={() => setUnwrappedChunk(unwrappedChunk === chunk.rank ? null : chunk.rank)}>
                {unwrappedChunk === chunk.rank ? 'Wrap long lines' : 'Preserve table rows ↔'}
              </button>
            </div>}
            <div className="chunk-viewport">
              <ChunkText text={chunk.text} unwrapped={unwrappedChunk === chunk.rank} />
            </div>
          </details>
        })}
      </div>
      <p className="evidence-footnote">
        Passages are consultable sources, not claim-level citations. The SEC link opens the full
        submission, not a precise passage.
      </p>
    </>
  )
}
