import { useEffect, useRef, useState } from 'react'
import { postChat } from '../api'
import type { ChatResponse, FilingSummary } from '../api'
import { FilingSelector } from './FilingSelector'
import { LiveAnswer } from './LiveAnswer'

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
    if (next.filing_id === filing?.filing_id) return
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
    if (target === null || text === '' || pending) return
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

  const canSend = filing !== null && !pending && draft.trim() !== ''

  return (
    <section aria-labelledby="chat-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">01 / Live filing chat</p>
          <h2 id="chat-heading">Ask a verified filing.</h2>
        </div>
        <p className="section-caption">
          Each question is independent. Refreshing the page clears these messages.
        </p>
      </div>
      <div className="explorer-grid">
        <div>
          <FilingSelector
            selectedId={filing?.filing_id ?? null}
            onSelect={handleSelect}
          />
        </div>
        <div className="case-content">
          <form className="answer-panel chat-form" aria-label="Ask the selected filing" onSubmit={onSubmit}>
            <label htmlFor="chat-question">
              {filing === null
                ? 'Question'
                : `Question about ${filing.company} ${filing.filing_year}`}
            </label>
            <textarea
              id="chat-question"
              rows={3}
              maxLength={2000}
              value={draft}
              disabled={filing === null || pending}
              placeholder="How does the filing describe revenue recognition?"
              onChange={event => setDraft(event.target.value)}
            />
            <div className="selector-nav">
              <span>{draft.trim().length}/2000</span>
              <button type="submit" disabled={!canSend}>
                {pending ? 'Waiting for the model…' : 'Send →'}
              </button>
            </div>
          </form>
          <div aria-live="polite">
            {messages.map(message => (
              <article className="answer-panel" key={message.id} aria-label={`Answer to ${message.question}`}>
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">
                      {message.filing.company} · {message.filing.filing_year}
                    </p>
                    <h3>{message.question}</h3>
                  </div>
                </div>
                {message.status === 'pending' && (
                  <div className="load-message" role="status">Waiting for the model…</div>
                )}
                {message.status === 'error' && (
                  <div className="load-message load-error" role="alert">
                    <h2>Live answer unavailable</h2>
                    <p>{message.error ?? 'The question could not be answered.'}</p>
                    <button
                      type="button"
                      className="button button-primary"
                      onClick={() => void send(message.question, message.id)}
                    >
                      Retry
                    </button>
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
