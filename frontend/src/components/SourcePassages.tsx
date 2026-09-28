import { useState } from 'react'
import type { RetrievedChunk } from '../api'
import { ChunkText } from './ChunkText'

interface Props {
  chunks: RetrievedChunk[]
  secUrl: string
}

export function SourcePassages({ chunks, secUrl }: Props) {
  const [unwrappedChunk, setUnwrappedChunk] = useState<number | null>(null)

  return (
    <details className="group mt-5 rounded-lg border border-[#dce5dd] bg-[#fafbf9]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3
        text-[.78rem] font-semibold text-[#315b4e] [&::-webkit-details-marker]:hidden">
        <span>Sources from this filing</span>
        <span className="font-normal text-[#72847a]">
          {chunks.length} {chunks.length === 1 ? 'source' : 'sources'}
          <span className="ml-2 inline-block transition-transform group-open:rotate-180" aria-hidden="true">⌄</span>
        </span>
      </summary>
      <div className="border-t border-[#e0e8e0] px-4 pb-4">
        <p className="mt-3 mb-4 text-[.73rem] leading-[1.6] text-[#708078]">
          These passages provide context for the answer. Check the original filing for important details.
        </p>
        <div className="grid gap-2">
          {chunks.map((chunk, index) => {
            const hasTable = /\|\s*-{3,}/.test(chunk.text)
            return (
              <details key={chunk.rank} className="group/passage min-w-0 rounded-md border
                border-[#e0e7e0] bg-white open:border-[#bad3c0]">
                <summary className="flex cursor-pointer list-none items-center gap-3 px-3 py-3
                  text-[.76rem] text-[#40584e] [&::-webkit-details-marker]:hidden">
                  <span className="shrink-0 font-semibold text-[#2d6d5f]">Source {index + 1}</span>
                  <span className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap
                    text-[#809087]">{chunk.text.slice(0, 90).replace(/\s+/g, ' ')}…</span>
                  <span className="text-[#70917b] group-open/passage:rotate-180" aria-hidden="true">⌄</span>
                </summary>
                <div className="mx-3 mb-3 border-t border-[#edf0ea]">
                  {hasTable && (
                    <button type="button" className="mt-3 rounded border border-[#d9e5db] bg-white
                      px-2 py-1 font-sans text-[.7rem] text-[#386b57] hover:bg-[#f1f7f2]"
                      aria-pressed={unwrappedChunk === chunk.rank}
                      onClick={() => setUnwrappedChunk(unwrappedChunk === chunk.rank ? null : chunk.rank)}>
                      {unwrappedChunk === chunk.rank ? 'Wrap long lines' : 'Keep table rows together'}
                    </button>
                  )}
                  <div className="max-h-[280px] overflow-auto">
                    <ChunkText text={chunk.text} unwrapped={unwrappedChunk === chunk.rank} />
                  </div>
                </div>
              </details>
            )
          })}
        </div>
        <a className="mt-4 inline-block text-[.76rem] font-semibold text-[#2d6d5f] underline-offset-4
          hover:underline" href={secUrl} target="_blank" rel="noopener noreferrer">
          Open the complete filing on SEC.gov ↗
        </a>
      </div>
    </details>
  )
}
