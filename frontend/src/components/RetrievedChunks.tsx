import { useState } from 'react'
import { ChunkText } from './ChunkText'
import {
  chunkCard, chunkList, chunkPreview, chunkRank, chunkScore, chunkSummary, chunkViewOptions,
  chunkViewport, evidenceFootnote, evidenceTitle, rankCount, retrievedHeading,
} from '../ui'

interface Props {
  chunks: { rank: number; score: number; text: string }[]
  description: string
  count: string
  note: string
}

export function RetrievedChunks({ chunks, description, count, note }: Props) {
  const [unwrappedChunk, setUnwrappedChunk] = useState<number | null>(null)

  return (
    <>
      <div className={retrievedHeading}>
        <div>
          <h4 className={evidenceTitle}>Retrieved context</h4>
          <p className="mt-[5px] mb-0 text-[.73rem] text-[#778580]">{description}</p>
        </div>
        <span className={rankCount}>{count}</span>
      </div>
      <div className={chunkList}>
        {chunks.map(chunk => {
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
      <p className={evidenceFootnote}>{note}</p>
    </>
  )
}
