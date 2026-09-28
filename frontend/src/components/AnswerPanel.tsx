import { reviewLabel } from '../labels'
import type { Example } from '../types'
import { VerdictBadge } from './VerdictBadge'

interface Props {
  example: Example
}

export function AnswerPanel({ example }: Props) {
  const { review } = example
  return (
    <section className="min-w-0 rounded-[5px] border border-[#dce2dc] bg-white p-8"
      aria-labelledby="answer-heading">
      <div className="mb-[30px] flex items-start justify-between gap-[25px]">
        <div>
          <p className="mt-0 mb-[13px] text-[.7rem] leading-[1.4] font-extrabold tracking-[.15em]
            text-[#55877b] uppercase">Question / {example.id}</p>
          <h3 id="answer-heading" className="m-0 max-w-[650px] font-display
            text-[clamp(1.45rem,2.4vw,2rem)] leading-[1.3] font-normal"
            aria-live="polite">{example.question}</h3>
        </div>
        <VerdictBadge review={review} className="mt-[3px] shrink-0" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="min-h-[163px] min-w-0 rounded bg-[#f0f5f1] p-[21px]">
          <div className="mb-[15px] flex items-center gap-2 text-[.7rem] font-[820] tracking-[.06em]
            text-[#506d66] uppercase">
            <span className="size-[9px] rounded-full border-2 border-current" /> Saved model answer
          </div>
          <p className="m-0 text-[.86rem] leading-[1.75] whitespace-pre-wrap [overflow-wrap:anywhere]">
            {example.generated_answer || 'No answer was saved.'}
          </p>
        </div>
        <div className="min-h-[163px] min-w-0 rounded bg-[#f6f4ed] p-[21px]">
          <div className="mb-[15px] flex items-center gap-2 text-[.7rem] font-[820] tracking-[.06em]
            text-[#877457] uppercase">
            <span className="size-[9px] rounded-full border-2 border-current" /> Gold reference
          </div>
          <p className="m-0 text-[.86rem] leading-[1.75] whitespace-pre-wrap [overflow-wrap:anywhere]">
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
          <p className="mt-0 mb-[9px] text-[.7rem] leading-[1.4] font-extrabold tracking-[.15em]
            text-[#55877b] uppercase">Answer assessment</p>
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
