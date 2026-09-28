import { SourcePassages } from './SourcePassages'
import type { ChatResponse } from '../api'

interface Props {
  answer: ChatResponse
}

export function LiveAnswer({ answer }: Props) {
  return (
    <>
      <p className="m-0 text-[.88rem] leading-[1.85] whitespace-pre-wrap text-[#263d39]
        [overflow-wrap:anywhere]">
        {answer.answer}
      </p>
      <SourcePassages chunks={answer.retrieved_chunks} secUrl={answer.sec_url} />
    </>
  )
}
