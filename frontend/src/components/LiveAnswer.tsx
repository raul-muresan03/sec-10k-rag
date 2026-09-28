import { RetrievedChunks } from './RetrievedChunks'
import type { ChatResponse } from '../api'
import { answerText, inlineLink, selectorContext } from '../ui'

interface Props {
  answer: ChatResponse
}

export function LiveAnswer({ answer }: Props) {
  const times = answer.stage_times_seconds

  return (
    <>
      <p className={answerText}>{answer.answer}</p>
      <p className={selectorContext}>
        Filing ID: {answer.filing_id}
        {' · '}{answer.model} · retrieval {times.retrieval.toFixed(2)}s
        {' · '}generation {times.generation.toFixed(2)}s
        {' · '}total {times.total.toFixed(2)}s
        {' · '}Request ID: {answer.request_id}
        {' · '}<a className={inlineLink} href={answer.sec_url} target="_blank" rel="noopener noreferrer">
          SEC filing ↗
        </a>
      </p>
      <RetrievedChunks chunks={answer.retrieved_chunks}
        count={String(answer.retrieved_chunks.length).padStart(2, '0')}
        description="Live top chunks from this filing, in rank order."
        note="Passages are consultable sources, not claim-level citations. The SEC link opens the full submission, not a precise passage." />
    </>
  )
}
