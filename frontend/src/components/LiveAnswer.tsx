import { useState } from 'react'
import { ChunkText } from './ChunkText'
import type { ChatResponse } from '../api'
import {
  answerText, chunkCard, chunkList, chunkPreview, chunkRank, chunkScore, chunkSummary,
  chunkViewOptions, chunkViewport, evidenceFootnote, evidenceTitle, inlineLink, rankCount,
  retrievedHeading, selectorContext,
} from '../ui'

interface Props {
  answer: ChatResponse
}

export function LiveAnswer({ answer }: Props) {
  const [unwrappedChunk, setUnwrappedChunk] = useState<number | null>(null)
  const times = answer.stage_times_seconds

  return (
    <>
      <p className={answerText}>{answer.answer}</p>
      <p className={selectorContext}>
        Filing ID: {answer.filing_id}
        {' · '}{answer.model} · retrieval {times.retrieval.toFixed(2)}s
        {' · '}generation {times.generation.toFixed(2)}s
        {' · '}total {times.total.toFixed(2)}s
        {' · '}Request ID: {answer.request_id}
        {' · '}<a className={inlineLink} href={answer.sec_url} target="_blank" rel="noopener noreferrer">
          SEC filing ↗
        </a>
      </p>
      <div className={retrievedHeading}>
        <div>
          <h4 className={evidenceTitle}>Retrieved context</h4>
          <p className="mt-[5px] mb-0 text-[.73rem] text-[#778580]">
            Live top chunks from this filing, in rank order.
          </p>
        </div>
        <span className={rankCount}>{String(answer.retrieved_chunks.length).padStart(2, '0')}</span>
      </div>
      <div className={chunkList}>
        {answer.retrieved_chunks.map(chunk => {
          const hasTable = /\|\s*-{3,}/.test(chunk.text)
          return <details key={chunk.rank} className={`${chunkCard} chunk`} open={chunk.rank === 1}>
            <summary className={chunkSummary}>
              <span className={chunkRank}>R{chunk.rank}</span>
              <span className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
                Retrieved passage <span className={chunkPreview}>· {chunk.text.slice(0, 65)}…</span>
              </span>
              <span className={chunkScore}>Similarity {chunk.score.toFixed(3)}</span>
            </summary>
            {hasTable && <div className={chunkViewOptions}>
              <button type="button" className="border-0 bg-transparent text-[.7rem] font-[750]
                text-[#2b6f61] underline underline-offset-[3px]" aria-pressed={unwrappedChunk === chunk.rank}
                onClick={() => setUnwrappedChunk(unwrappedChunk === chunk.rank ? null : chunk.rank)}>
                {unwrappedChunk === chunk.rank ? 'Wrap long lines' : 'Preserve table rows ↔'}
              </button>
            </div>}
            <div className={chunkViewport}>
              <ChunkText text={chunk.text} unwrapped={unwrappedChunk === chunk.rank} />
            </div>
          </details>
        })}
      </div>
      <p className={evidenceFootnote}>
        Passages are consultable sources, not claim-level citations. The SEC link opens the full
        submission, not a precise passage.
      </p>
    </>
  )
}
