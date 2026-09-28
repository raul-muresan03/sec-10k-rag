import { exampleLabel, reviewLabel, verdictLabel } from '../labels'
import type { Example } from '../types'
import { eyebrow, selectorContext } from '../ui'

interface Props {
  examples: Example[]
  selected: Example
  onSelect: (id: string) => void
}

export function ExampleSelector({ examples, selected, onSelect }: Props) {
  const index = examples.findIndex(example => example.id === selected.id)
  return (
    <div className="selector-panel">
      <div className="selector-topline">
        <span className={eyebrow}>Case file</span>
        <span className="case-count">
          {String(index + 1).padStart(2, '0')} / {String(examples.length).padStart(2, '0')}
        </span>
      </div>
      <label htmlFor="case-select">Choose a saved question</label>
      <select id="case-select" value={selected.id} onChange={event => onSelect(event.target.value)}>
        {examples.map(example => (
          <option key={example.id} value={example.id}>{exampleLabel(example)}</option>
        ))}
      </select>
      <div className="selector-nav">
        <button type="button" onClick={() => onSelect(examples[(index - 1 + examples.length) % examples.length].id)}>
          <span aria-hidden="true">←</span> Previous
        </button>
        <button type="button" onClick={() => onSelect(examples[(index + 1) % examples.length].id)}>
          Next <span aria-hidden="true">→</span>
        </button>
      </div>
      <div className="selector-status">
        <span className={`verdict-chip ${selected.review.verdict ?? 'unreviewed'}`}>
          {verdictLabel(selected.review)}
        </span>
        <span>{reviewLabel(selected.review)}</span>
      </div>
      <p className={selectorContext}>
        {selected.id} · Filing {selected.filing_year} · {selected.question_type.replace('_', '-')}
      </p>
    </div>
  )
}
