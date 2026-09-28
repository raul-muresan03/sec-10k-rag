import { useState } from 'react'
import { ChunkText } from './ChunkText'
import type { Example } from '../types'
import {
  chunkCard, chunkList, chunkPreview, chunkRank, chunkScore, chunkSummary, chunkViewOptions,
  chunkViewport, eyebrow, evidenceFootnote, evidenceLabelRow, evidencePanel, evidenceTitle,
  inlineLink, rankCount, retrievedHeading,
} from '../ui'

interface Props {
  example: Example
}

export function EvidencePanel({ example }: Props) {
  const [unwrappedChunk, setUnwrappedChunk] = useState<string | null>(null)

  return (
    <section className={evidencePanel} aria-labelledby="evidence-heading">
      <div className="flex flex-wrap items-start justify-between gap-[15px]">
        <div>
          <p className={`${eyebrow} mb-2`}>Trace the evidence</p>
          <h3 id="evidence-heading" className="mb-0 font-display text-[1.5rem] font-normal">
            What did the system see?
          </h3>
        </div>
        <a href={example.sec_url} target="_blank" rel="noopener noreferrer" className={`${inlineLink} mt-3`}>
          SEC filing <span aria-hidden="true">↗</span>
        </a>
      </div>

      <div className="mt-[27px] rounded-[3px] border border-[#e5e4d9] bg-[#fcfbf6] p-5">
        <div className={evidenceLabelRow}>
          <h4 className={evidenceTitle}>Gold reference evidence</h4>
          <span className="text-[.68rem] text-[#879189]">Quoted passages from the evaluation set</span>
        </div>
        {example.reference_evidence.length ? (
          <ol className="mt-[14px] mb-0 pl-[18px]">
            {example.reference_evidence.map((quote, index) => (
              <li className="mt-[10px] pl-1" key={index}>
                <blockquote className="mx-0 mt-0 mb-2 text-[.81rem] leading-[1.65] text-[#41544f]">
                  {quote}
                </blockquote>
                <span className={`text-[.69rem] font-[750] ${example.answer_run_evidence_found[index]
                  ? 'text-[#277260]' : 'text-[#9b583e]'}`}>
                  {example.answer_run_evidence_found[index]
                    ? 'Strict match in saved top 5' : 'No strict match in saved top 5'}
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-3 mb-0 text-[.8rem] text-[#67766c]">
            Not applicable — no gold passage is assigned to this no-answer question.
          </p>
        )}
      </div>

      <div className={retrievedHeading}>
        <div>
          <h4 className={evidenceTitle}>Retrieved context</h4>
          <p className="mt-[5px] mb-0 text-[.73rem] text-[#778580]">
            Complete saved top-five chunks from the answer run, in original rank order.
          </p>
        </div>
        <span className={rankCount}>01—05</span>
      </div>
      <div className={chunkList}>
        {example.retrieved_context.map(chunk => {
          const chunkId = `${example.id}-${chunk.rank}`
          const hasTable = /\|\s*-{3,}/.test(chunk.text)
          return <details key={chunkId} className={`${chunkCard} chunk`} open={chunk.rank === 1}>
            <summary className={chunkSummary}>
              <span className={chunkRank}>R{chunk.rank}</span>
              <span className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
                Retrieved passage <span className={chunkPreview}>· {chunk.text.slice(0, 65)}…</span>
              </span>
              <span className={chunkScore}>Similarity {chunk.score.toFixed(3)}</span>
            </summary>
            {hasTable && <div className={chunkViewOptions}>
              <button type="button" className="border-0 bg-transparent text-[.7rem] font-[750]
                text-[#2b6f61] underline underline-offset-[3px]" aria-pressed={unwrappedChunk === chunkId}
                onClick={() => setUnwrappedChunk(unwrappedChunk === chunkId ? null : chunkId)}>
                {unwrappedChunk === chunkId ? 'Wrap long lines' : 'Preserve table rows ↔'}
              </button>
            </div>}
            <div className={chunkViewport}>
              <ChunkText text={chunk.text} unwrapped={unwrappedChunk === chunkId} />
            </div>
          </details>
        })}
      </div>
      <p className={evidenceFootnote}>
        The SEC link opens the full submission, not a precise passage citation. A missing strict quote can still have
        equivalent table evidence; inspect the actual context before diagnosing retrieval.
      </p>
    </section>
  )
}
