import { useEffect, useRef, useState } from 'react'
import { postChat } from '../api'
import type { ChatResponse, FilingSummary } from '../api'
import {
  answerPanel, caseContent, eyebrow, explorerGrid, loadErrorTitle, loadMessage, panelHeading,
  panelTitle, selectorContext,
} from '../ui'
import { FilingSelector } from './FilingSelector'
import { LiveAnswer } from './LiveAnswer'
import { PrimaryButton } from './PrimaryButton'
import { SectionHeading } from './SectionHeading'

const CLIENT_TIMEOUT_MS = 125_000

interface Message {
  id: number
  filing: FilingSummary
  question: string
  status: 'pending' | 'done' | 'error'
  answer?: ChatResponse
  error?: string
}

export function ChatView() {
  const [filing, setFiling] = useState<FilingSummary | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const sessionRef = useRef(0)
  const messageRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const handleSelect = (next: FilingSummary) => {
    if (next.filing_id === filing?.filing_id) {
      setFiling(previous => previous?.status === next.status && previous.detail === next.detail ? previous : next)
      return
    }
    abortRef.current?.abort()
    abortRef.current = null
    sessionRef.current += 1
    setFiling(next)
    setMessages([])
    setPending(false)
  }

  const send = async (question: string, messageId?: number) => {
    const target = filing
    const text = question.trim()
    if (target === null || target.status !== 'ready' || text === '' || pending) return
    const session = sessionRef.current
    const id = messageId ?? ++messageRef.current
    if (messageId === undefined) {
      setMessages(previous => [
        ...previous,
        { id, filing: target, question: text, status: 'pending' },
      ])
    } else {
      setMessages(previous => previous.map(message =>
        message.id === id ? { ...message, status: 'pending', error: undefined } : message,
      ))
    }
    setPending(true)
    const controller = new AbortController()
    abortRef.current = controller
    let timedOut = false
    const timer = setTimeout(() => {
      timedOut = true
      controller.abort()
    }, CLIENT_TIMEOUT_MS)
    try {
      const answer = await postChat(target.filing_id, text, controller.signal)
      if (sessionRef.current !== session) return
      setMessages(previous => previous.map(message =>
        message.id === id ? { ...message, status: 'done', answer } : message,
      ))
    } catch (reason) {
      if (sessionRef.current !== session) return
      const message = reason instanceof Error && reason.name === 'AbortError' && timedOut
        ? 'The request timed out. Try a shorter question.'
        : reason instanceof Error
          ? reason.message
          : 'The question could not be answered.'
      setMessages(previous => previous.map(item =>
        item.id === id ? { ...item, status: 'error', error: message } : item,
      ))
    } finally {
      clearTimeout(timer)
      if (abortRef.current === controller) abortRef.current = null
      if (sessionRef.current === session) setPending(false)
    }
  }

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const text = draft.trim()
    if (text === '') return
    setDraft('')
    void send(text)
  }

  const canSend = filing?.status === 'ready' && !pending && draft.trim() !== ''

  return (
    <section aria-labelledby="chat-heading">
      <SectionHeading id="chat-heading" eyebrow="01 / Live filing chat" title="Ask a verified filing."
        caption="Each question is independent. Refreshing the page clears these messages." />
      <div className={explorerGrid}>
        <div>
          <FilingSelector
            selectedId={filing?.filing_id ?? null}
            onSelect={handleSelect}
          />
        </div>
        <div className={caseContent}>
          <form className={answerPanel} aria-label="Ask the selected filing" onSubmit={onSubmit}>
            <label className="mb-3 block text-[.82rem] font-[750] text-[#385450]" htmlFor="chat-question">
              {filing === null
                ? 'Question'
                : `Question about ${filing.company} ${filing.filing_year}`}
            </label>
            <textarea
              id="chat-question"
              className="block min-h-[120px] w-full resize-y rounded-[3px] border border-[#bfcac4]
                bg-[#f9faf7] p-[14px] leading-[1.6] text-[#1d3032] placeholder:text-[#697978]"
              rows={3}
              maxLength={2000}
              value={draft}
              disabled={filing?.status !== 'ready' || pending}
              placeholder="How does the filing describe revenue recognition?"
              onChange={event => setDraft(event.target.value)}
            />
            {filing && filing.status !== 'ready' && (
              <p className={selectorContext} role="status">
                Prepare {filing.company} from the filing selector before asking questions.
              </p>
            )}
            <div className="mt-[14px] flex items-center justify-between gap-[10px]
              text-[.75rem] text-[#65737b]">
              <span>{draft.trim().length}/2000</span>
              <button type="submit" className="min-h-11 rounded-[3px] border border-[#bdd6cc]
                bg-[#e9f2ed] px-[18px] py-2 text-[.74rem] font-[750] text-[#205f50]
                hover:underline hover:underline-offset-4 disabled:cursor-not-allowed disabled:opacity-55"
                disabled={!canSend}>
                {pending ? 'Waiting for the model…' : 'Send →'}
              </button>
            </div>
          </form>
          <div aria-live="polite">
            {messages.map(message => (
              <article className={answerPanel} key={message.id} aria-label={`Answer to ${message.question}`}>
                <div className={panelHeading}>
                  <div>
                    <p className={`${eyebrow} mb-[13px]`}>
                      {message.filing.company} · {message.filing.filing_year}
                    </p>
                    <h3 className={panelTitle}>{message.question}</h3>
                  </div>
                </div>
                {message.status === 'pending' && (
                  <div className={loadMessage} role="status">Waiting for the model…</div>
                )}
                {message.status === 'error' && (
                  <div className={loadMessage} role="alert">
                    <h2 className={loadErrorTitle}>Live answer unavailable</h2>
                    <p>{message.error ?? 'The question could not be answered.'}</p>
                    <PrimaryButton
                      type="button"
                      className="mt-[10px]"
                      onClick={() => void send(message.question, message.id)}
                    >
                      Retry
                    </PrimaryButton>
                  </div>
                )}
                {message.status === 'done' && message.answer && (
                  <LiveAnswer answer={message.answer} />
                )}
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
