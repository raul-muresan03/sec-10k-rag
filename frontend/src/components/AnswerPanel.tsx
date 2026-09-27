import { reviewLabel, verdictLabel } from '../labels'
import type { Example } from '../types'

interface Props {
  example: Example
}

export function AnswerPanel({ example }: Props) {
  const { review } = example
  return (
    <section className="answer-panel" aria-labelledby="answer-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Question / {example.id}</p>
          <h3 id="answer-heading" aria-live="polite">{example.question}</h3>
        </div>
        <span className={`verdict-chip ${review.verdict ?? 'unreviewed'}`}>
          {verdictLabel(review)}
        </span>
      </div>

      <div className="answer-columns">
        <div className="answer-block generated">
          <div className="block-label"><span className="label-mark" /> Saved model answer</div>
          <p className="answer-text">{example.generated_answer || 'No answer was saved.'}</p>
        </div>
        <div className="answer-block reference">
          <div className="block-label"><span className="label-mark" /> Gold reference</div>
          <p className="answer-text">
            {example.reference_answer ?? 'No answer expected from the available filing context.'}
          </p>
          {example.reference_verification_note && (
            <p className="verification-note">Gold-label note: {example.reference_verification_note}</p>
          )}
        </div>
      </div>

      <div className="review-box">
        <div className="review-title-row">
          <p className="eyebrow">Answer assessment</p>
          <span className="review-source">{reviewLabel(review)}
            {review.confidence && ` · ${review.confidence} confidence`}</span>
        </div>
        <p>{review.explanation || 'This answer has not been reviewed yet.'}</p>
        <details className="dimensions">
          <summary>Review dimensions <span aria-hidden="true">↗</span></summary>
          <dl>
            {Object.entries(review.dimensions).map(([name, value]) => (
              <div key={name}>
                <dt>{name.replace('_', ' ')}</dt>
                <dd>
                  {value === 'not_applicable' ? 'Not applicable' : value === 'not_assessed' ? 'Not assessed' : value}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      </div>
    </section>
  )
}
