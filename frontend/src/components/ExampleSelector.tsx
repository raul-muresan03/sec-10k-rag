import { exampleLabel, reviewLabel } from '../labels'
import type { Example } from '../types'
import {
  caseCount, eyebrow, selectorContext, selectorControl, selectorLabel, selectorPanel, selectorTopline,
} from '../ui'
import { VerdictBadge } from './VerdictBadge'

interface Props {
  examples: Example[]
  selected: Example
  onSelect: (id: string) => void
}

export function ExampleSelector({ examples, selected, onSelect }: Props) {
  const index = examples.findIndex(example => example.id === selected.id)
  return (
    <div className={selectorPanel}>
      <div className={selectorTopline}>
        <span className={eyebrow}>Case file</span>
        <span className={caseCount}>
          {String(index + 1).padStart(2, '0')} / {String(examples.length).padStart(2, '0')}
        </span>
      </div>
      <label className={selectorLabel} htmlFor="case-select">Choose a saved question</label>
      <select className={selectorControl} id="case-select" value={selected.id}
        onChange={event => onSelect(event.target.value)}>
        {examples.map(example => (
          <option key={example.id} value={example.id}>{exampleLabel(example)}</option>
        ))}
      </select>
      <div className="mt-[13px] mb-6 flex items-center justify-between gap-[10px]">
        <button type="button" className="border-0 bg-transparent px-0 py-[5px] text-[.74rem]
          font-[750] text-[#2e7565] hover:underline hover:underline-offset-4"
          onClick={() => onSelect(examples[(index - 1 + examples.length) % examples.length].id)}>
          <span aria-hidden="true">←</span> Previous
        </button>
        <button type="button" className="border-0 bg-transparent px-0 py-[5px] text-[.74rem]
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
      <p className={selectorContext}>
        {selected.id} · Filing {selected.filing_year} · {selected.question_type.replace('_', '-')}
      </p>
    </div>
  )
}
