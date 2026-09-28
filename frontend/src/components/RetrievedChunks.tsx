import { useState } from 'react'
import { ChunkText } from './ChunkText'

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
      <div className="mt-[30px] mb-[15px] flex flex-wrap items-baseline justify-between gap-x-[18px] gap-y-[6px]">
        <div>
          <h4 className="m-0 text-[.82rem] tracking-[-.015em]">Retrieved context</h4>
          <p className="mt-[5px] mb-0 text-[.73rem] text-[#778580]">{description}</p>
        </div>
        <span className="font-code text-[.72rem] text-[#8a9b91]">{count}</span>
      </div>
      <div className="grid gap-2">
        {chunks.map(chunk => {
          const hasTable = /\|\s*-{3,}/.test(chunk.text)
          return <details key={chunk.rank} className="group min-w-0 rounded-[3px] border border-[#e0e6e0]
            bg-white open:border-[#bbd4c3] open:bg-[#fbfdfb]" open={chunk.rank === 1}>
            <summary className="flex cursor-pointer list-none items-center gap-3 px-[14px] py-3 text-[.75rem]
              [&::-webkit-details-marker]:hidden after:order-5 after:text-base after:text-[#568172]
              after:content-['+'] group-open:after:content-['−']">
              <span className="grid h-[27px] w-8 shrink-0 place-items-center rounded-[3px] bg-[#eaf3ec]
                font-code font-extrabold text-[#29705f]">R{chunk.rank}</span>
              <span className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
                Retrieved passage <span className="font-normal text-[#83908c]">
                  · {chunk.text.slice(0, 65)}…
                </span>
              </span>
              <span className="shrink-0 font-code text-[.68rem] text-[#82908a]">
                Similarity {chunk.score.toFixed(3)}
              </span>
            </summary>
            {hasTable && <div className="flex justify-end px-[14px] pb-[9px]">
              <button type="button" className="border-0 bg-transparent font-sans text-[.7rem] font-[750]
                text-[#2b6f61] underline underline-offset-[3px]" aria-pressed={unwrappedChunk === chunk.rank}
                onClick={() => setUnwrappedChunk(unwrappedChunk === chunk.rank ? null : chunk.rank)}>
                {unwrappedChunk === chunk.rank ? 'Wrap long lines' : 'Preserve table rows ↔'}
              </button>
            </div>}
            <div className="mx-[14px] mb-[14px] max-h-[360px] overflow-auto border-t border-[#e5ebe6]">
              <ChunkText text={chunk.text} unwrapped={unwrappedChunk === chunk.rank} />
            </div>
          </details>
        })}
      </div>
      <p className="mt-[17px] mb-0 text-[.7rem] leading-[1.65] text-[#7d8887]">{note}</p>
    </>
  )
}
