import { exampleLabel, reviewLabel } from '../labels'
import type { Example } from '../types'
import { VerdictBadge } from './VerdictBadge'

interface Props {
  examples: Example[]
  selected: Example
  onSelect: (id: string) => void
}

export function ExampleSelector({ examples, selected, onSelect }: Props) {
  const index = examples.findIndex(example => example.id === selected.id)
  return (
    <div className="sticky top-5 min-w-0 rounded-[5px] border border-[#dce2dc] bg-white p-[23px]">
      <div className="flex items-center justify-between gap-[10px]">
        <span className="text-[.7rem] leading-[1.4] font-extrabold tracking-[.15em] text-[#55877b]
          uppercase">Case file</span>
        <span className="font-code text-[.72rem] text-[#687878]">
          {String(index + 1).padStart(2, '0')} / {String(examples.length).padStart(2, '0')}
        </span>
      </div>
      <label className="mt-7 mb-[9px] block text-[.78rem] font-[760]" htmlFor="case-select">
        Choose a saved question
      </label>
      <select className="min-h-[46px] w-full rounded-[3px] border border-[#bfcac4] bg-[#f9faf7] font-sans
        py-[9px] pr-[31px] pl-[11px] text-[.77rem] text-[#1d3032]" id="case-select" value={selected.id}
        onChange={event => onSelect(event.target.value)}>
        {examples.map(example => (
          <option key={example.id} value={example.id}>{exampleLabel(example)}</option>
        ))}
      </select>
      <div className="mt-[13px] mb-6 flex items-center justify-between gap-[10px]">
        <button type="button" className="border-0 bg-transparent px-0 py-[5px] font-sans text-[.74rem]
          font-[750] text-[#2e7565] hover:underline hover:underline-offset-4"
          onClick={() => onSelect(examples[(index - 1 + examples.length) % examples.length].id)}>
          <span aria-hidden="true">←</span> Previous
        </button>
        <button type="button" className="border-0 bg-transparent px-0 py-[5px] font-sans text-[.74rem]
          font-[750] text-[#2e7565] hover:underline hover:underline-offset-4"
          onClick={() => onSelect(examples[(index + 1) % examples.length].id)}>
          Next <span aria-hidden="true">→</span>
        </button>
      </div>
      <div className="flex flex-wrap items-center justify-start gap-[10px] border-t border-[#e4e9e5]
        pt-[21px] text-[.7rem] text-[#637273]">
        <VerdictBadge review={selected.review} />
        <span>{reviewLabel(selected.review)}</span>
      </div>
      <p className="mt-[14px] mb-0 font-code text-[.65rem] leading-[1.6] text-[#8b9794]
        [overflow-wrap:anywhere]">
        {selected.id} · Filing {selected.filing_year} · {selected.question_type.replace('_', '-')}
      </p>
    </div>
  )
}
