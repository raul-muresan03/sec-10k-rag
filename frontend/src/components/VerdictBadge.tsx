import { verdictLabel } from '../labels'
import type { Review } from '../types'

interface Props {
  review: Review
  className?: string
}

export function VerdictBadge({ review, className = '' }: Props) {
  return (
    <span className={`inline-flex w-max max-w-full items-center rounded-[3px] px-[10px] py-[7px]
      text-[.7rem] font-extrabold tracking-[.035em] uppercase
      ${review.verdict === 'pass' ? 'bg-[#e1f2ea] text-[#196457]'
        : review.verdict === 'partial' ? 'bg-[#fff1d9] text-[#855721]'
          : review.verdict === 'incorrect' ? 'bg-[#fde7e1] text-[#a14335]'
            : 'bg-[#eaeef0] text-[#59636b]'} ${className}`}>
      {verdictLabel(review)}
    </span>
  )
}
