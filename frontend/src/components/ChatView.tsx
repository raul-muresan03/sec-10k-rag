import { useEffect, useRef, useState } from 'react'
import { ApiError, postChat } from '../api'
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
  const conversationRef = useRef<HTMLDivElement | null>(null)
  const questionRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])
  useEffect(() => {
    if (conversationRef.current) conversationRef.current.scrollTop = conversationRef.current.scrollHeight
  }, [messages])

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
    setDraft('')
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
        ? 'This is taking longer than expected. Please try again.'
        : reason instanceof ApiError
          ? reason.message
          : 'We couldn’t answer that right now. Please try again.'
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

  const ready = filing?.status === 'ready'
  const canSend = ready && !pending && draft.trim() !== ''

  return (
    <section className="grid h-[calc(100vh-73px)] min-h-[650px] grid-cols-[282px_minmax(0,1fr)]
      border-x border-[#dce2dc]" aria-label="Filing chat">
      <aside className="flex min-w-0 flex-col border-r border-[#dce2dc] bg-[#f0f3ef] px-5 py-7">
        <div className="mb-7">
          <h2 className="mt-0 mb-2 font-display text-[1.5rem] font-normal">Your filing</h2>
          <p className="m-0 text-[.78rem] leading-[1.6] text-[#62746e]">
            Choose the annual report you want to explore.
          </p>
        </div>
        <FilingSelector selectedId={filing?.filing_id ?? null} onSelect={handleSelect} />
      </aside>
      <div className="flex min-h-0 min-w-0 flex-col bg-white">
        <div className="flex min-h-[72px] items-center justify-between gap-4 border-b border-[#e7ebe7] px-8">
          <div>
            <h1 id="chat-heading" className="m-0 text-[1.03rem] font-semibold text-[#20353b]">
              Chat with a filing
            </h1>
            <p className="mt-1 mb-0 text-[.72rem] text-[#72817c]">
              {filing ? `${filing.company} · ${filing.filing_year} annual filing` : 'Select an annual filing to begin'}
            </p>
          </div>
          {ready && <span className="inline-flex items-center gap-2 rounded-full bg-[#e9f3ec]
            px-3 py-1.5 text-[.7rem] font-semibold text-[#2d6855]">
            <span className="size-1.5 rounded-full bg-[#5aa47b]" aria-hidden="true" /> Ready to chat
          </span>}
        </div>

        <div ref={conversationRef} className="min-h-0 flex-1 overflow-y-auto px-8 py-8" aria-live="polite">
          {messages.length === 0 ? (
            <div className="mx-auto flex h-full max-w-[710px] flex-col justify-center pb-14">
              <span className="mb-5 grid size-12 place-items-center rounded-xl bg-[#e6eee8]
                font-display text-[1.45rem] text-[#2d6d5f]" aria-hidden="true">?</span>
              <h2 className="mt-0 mb-3 font-display text-[clamp(2rem,3vw,2.8rem)] font-normal
                leading-[1.15] text-[#20353b]">
                What would you like to know{filing ? ` about ${filing.company}` : ''}?
              </h2>
              <p className="mt-0 mb-8 max-w-[570px] text-[.9rem] leading-[1.7] text-[#657570]">
                Ask about the business, financial results, or risks in the selected annual filing.
              </p>
              <div className="grid grid-cols-3 gap-3" aria-label="Suggested questions">
                {[
                  'What risks does this filing highlight?',
                  'What does it report about revenue?',
                  'What does it say about cash flow?',
                ].map(prompt => (
                  <button key={prompt} type="button" className="min-h-[88px] rounded-lg border
                    border-[#dce5dd] bg-[#fafbf8] px-4 py-3 text-left font-sans text-[.79rem]
                    leading-[1.5] text-[#345a51] hover:border-[#9ebfad] hover:bg-[#f0f7f1]
                    disabled:cursor-not-allowed disabled:opacity-60" disabled={!ready}
                    onClick={() => { setDraft(prompt); questionRef.current?.focus() }}>
                    {prompt} <span className="block pt-1 text-[#7b9a89]" aria-hidden="true">↗</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto flex max-w-[760px] flex-col gap-8">
              {messages.map(message => (
                <div key={message.id}>
                  <div className="ml-auto w-fit max-w-[80%] rounded-2xl rounded-br-sm bg-[#e9f0e9]
                    px-5 py-3 text-[.88rem] leading-[1.7] whitespace-pre-wrap text-[#203b34]">
                    {message.question}
                  </div>
                  <div className="mt-6 flex items-start gap-3" aria-label={`Answer to ${message.question}`}>
                    <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-[#192b3b]
                      font-display text-[.66rem] text-[#e2cea9]" aria-hidden="true">10K</span>
                    <div className="min-w-0 flex-1 pt-1">
                      {message.status === 'pending' && (
                        <p className="m-0 text-[.85rem] text-[#687a74]" role="status">Reading the filing…</p>
                      )}
                      {message.status === 'error' && (
                        <div role="alert">
                          <p className="mt-0 mb-3 text-[.85rem] leading-[1.6] text-[#9b583e]">
                            {message.error ?? 'We couldn’t answer that right now. Please try again.'}
                          </p>
                          <button type="button" className="rounded-md border border-[#bdd4c6] bg-white
                            px-4 py-2 font-sans text-[.76rem] font-semibold text-[#2e6956] hover:bg-[#eef5ef]"
                            onClick={() => void send(message.question, message.id)}>Try again</button>
                        </div>
                      )}
                      {message.status === 'done' && message.answer && <LiveAnswer answer={message.answer} />}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <form className="border-t border-[#e7ebe7] bg-white px-8 py-5" onSubmit={onSubmit}
          aria-label="Ask the selected filing">
          <div className="mx-auto max-w-[760px]">
            <label className="sr-only" htmlFor="chat-question">Your question</label>
            <div className="flex items-end gap-3 rounded-xl border border-[#b8cac0] bg-[#fcfdfa]
              px-4 py-3 shadow-[0_5px_18px_#142e2010] focus-within:border-[#4e8b70]">
              <textarea id="chat-question" ref={questionRef} rows={2} maxLength={2000}
                className="max-h-[180px] min-h-[52px] flex-1 resize-y border-0 bg-transparent
                  font-sans text-[.9rem] leading-[1.6] text-[#20353b] outline-none
                  placeholder:text-[#8b9992]"
                value={draft} disabled={!ready || pending}
                placeholder={ready ? `Ask about ${filing.company}'s annual filing…`
                  : filing ? 'Questions are available when this filing is ready…' : 'Select a filing to begin…'}
                onChange={event => setDraft(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault()
                    event.currentTarget.form?.requestSubmit()
                  }
                }} />
              <button type="submit" className="grid size-10 shrink-0 place-items-center rounded-lg
                border-0 bg-[#2d6d5f] font-sans text-lg text-white hover:bg-[#20584c]
                disabled:cursor-not-allowed disabled:bg-[#b9c8be]" disabled={!canSend}
                aria-label="Send question" title="Send question">↑</button>
            </div>
            <p className="mt-2 mb-0 text-center text-[.68rem] text-[#829089]">
              Enter to send · Shift+Enter for a new line · Chats reset when you refresh
            </p>
            <p className="mt-1 mb-0 text-center text-[.68rem] text-[#829089]">
              Demo over six prepared 10-K filings · Questions and retrieved passages are sent to cloud
              model providers
            </p>
          </div>
        </form>
      </div>
    </section>
  )
}
