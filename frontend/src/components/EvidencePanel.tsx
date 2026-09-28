import { RetrievedChunks } from './RetrievedChunks'
import type { Example } from '../types'
import {
  eyebrow, evidenceLabelRow, evidencePanel, evidenceTitle, inlineLink,
} from '../ui'

interface Props {
  example: Example
}

export function EvidencePanel({ example }: Props) {
  return (
    <section className={evidencePanel} aria-labelledby="evidence-heading">
      <div className="flex flex-wrap items-start justify-between gap-[15px]">
        <div>
          <p className={`${eyebrow} mb-2`}>Trace the evidence</p>
          <h3 id="evidence-heading" className="mb-0 font-display text-[1.5rem] font-normal">
            What did the system see?
          </h3>
        </div>
        <a href={example.sec_url} target="_blank" rel="noopener noreferrer" className={`${inlineLink} mt-3`}>
          SEC filing <span aria-hidden="true">↗</span>
        </a>
      </div>

      <div className="mt-[27px] rounded-[3px] border border-[#e5e4d9] bg-[#fcfbf6] p-5">
        <div className={evidenceLabelRow}>
          <h4 className={evidenceTitle}>Gold reference evidence</h4>
          <span className="text-[.68rem] text-[#879189]">Quoted passages from the evaluation set</span>
        </div>
        {example.reference_evidence.length ? (
          <ol className="mt-[14px] mb-0 pl-[18px]">
            {example.reference_evidence.map((quote, index) => (
              <li className="mt-[10px] pl-1" key={index}>
                <blockquote className="mx-0 mt-0 mb-2 text-[.81rem] leading-[1.65] text-[#41544f]">
                  {quote}
                </blockquote>
                <span className={`text-[.69rem] font-[750] ${example.answer_run_evidence_found[index]
                  ? 'text-[#277260]' : 'text-[#9b583e]'}`}>
                  {example.answer_run_evidence_found[index]
                    ? 'Strict match in saved top 5' : 'No strict match in saved top 5'}
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-3 mb-0 text-[.8rem] text-[#67766c]">
            Not applicable — no gold passage is assigned to this no-answer question.
          </p>
        )}
      </div>

      <RetrievedChunks key={example.id} chunks={example.retrieved_context}
        count="01—05" description="Complete saved top-five chunks from the answer run, in original rank order."
        note="The SEC link opens the full submission, not a precise passage citation. A missing strict quote can still have equivalent table evidence; inspect the actual context before diagnosing retrieval." />
    </section>
  )
}
