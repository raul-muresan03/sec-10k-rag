import { reviewLabel, verdictLabel } from '../labels'
import type { Example } from '../types'
import { answerPanel, answerText, eyebrow, panelHeading, panelTitle, verdictBadge } from '../ui'

interface Props {
  example: Example
}

export function AnswerPanel({ example }: Props) {
  const { review } = example
  return (
    <section className={answerPanel} aria-labelledby="answer-heading">
      <div className={panelHeading}>
        <div>
          <p className={`${eyebrow} mb-[13px]`}>Question / {example.id}</p>
          <h3 id="answer-heading" className={panelTitle} aria-live="polite">{example.question}</h3>
        </div>
        <span className={`${verdictBadge(review.verdict)} mt-[3px] shrink-0`}>
          {verdictLabel(review)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="min-h-[163px] min-w-0 rounded bg-[#f0f5f1] p-[21px]">
          <div className="mb-[15px] flex items-center gap-2 text-[.7rem] font-[820] tracking-[.06em]
            text-[#506d66] uppercase">
            <span className="size-[9px] rounded-full border-2 border-current" /> Saved model answer
          </div>
          <p className={answerText}>{example.generated_answer || 'No answer was saved.'}</p>
        </div>
        <div className="min-h-[163px] min-w-0 rounded bg-[#f6f4ed] p-[21px]">
          <div className="mb-[15px] flex items-center gap-2 text-[.7rem] font-[820] tracking-[.06em]
            text-[#877457] uppercase">
            <span className="size-[9px] rounded-full border-2 border-current" /> Gold reference
          </div>
          <p className={answerText}>
            {example.reference_answer ?? 'No answer expected from the available filing context.'}
          </p>
          {example.reference_verification_note && (
            <p className="mt-4 mb-0 border-t border-[#e4ddcd] pt-3 text-[.72rem] leading-[1.6]
              text-[#7a6555]">Gold-label note: {example.reference_verification_note}</p>
          )}
        </div>
      </div>

      <div className="mt-[25px] border-t border-[#e4e9e5] pt-5">
        <div className="flex flex-wrap justify-between gap-2">
          <p className={`${eyebrow} mb-[9px]`}>Answer assessment</p>
          <span className="text-[.7rem] text-[#6f7c7d]">{reviewLabel(review)}
            {review.confidence && ` · ${review.confidence} confidence`}</span>
        </div>
        <p className="m-0 text-[.85rem] leading-[1.7]">
          {review.explanation || 'This answer has not been reviewed yet.'}
        </p>
        <details className="mt-[18px] [border-top:1px_dashed_#d7ded9]">
          <summary className="cursor-pointer pt-[13px] text-[.73rem] font-[750] text-[#367063]">
            Review dimensions <span className="ml-1" aria-hidden="true">↗</span>
          </summary>
          <dl className="mt-[15px] mb-0 grid grid-cols-2 gap-x-[22px] gap-y-[10px]">
            {Object.entries(review.dimensions).map(([name, value]) => (
              <div className="flex justify-between gap-[10px] border-b border-[#e9eee9] pb-2 text-[.73rem]"
                key={name}>
                <dt className="text-[#697575] capitalize">{name.replace('_', ' ')}</dt>
                <dd className="m-0 text-right font-bold capitalize">
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
