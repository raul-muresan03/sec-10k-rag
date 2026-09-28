import { ChatView } from './components/ChatView'

function App() {
  return (
    <div className="flex min-h-screen flex-col bg-[#f6f5f1]">
      <header className="border-b border-[#dce2dc] bg-white">
        <div className="mx-auto flex h-[72px] w-full max-w-[1440px] items-center justify-between px-8">
          <a className="inline-flex items-center gap-3 text-[#152331] no-underline" href="#chat"
            aria-label="SEC 10-K RAG home">
            <span className="grid size-10 place-items-center rounded-lg bg-[#192b3b] font-display
              text-[1rem] text-[#e2cea9]" aria-hidden="true">10K</span>
            <span className="grid gap-0.5">
              <strong className="text-[.93rem] tracking-[-.02em]">SEC 10-K RAG</strong>
              <span className="text-[.68rem] text-[#667875]">Annual filing assistant</span>
            </span>
          </a>
          <span className="text-[.75rem] text-[#667875]">Explore the filing. Find the evidence.</span>
        </div>
      </header>

      <main id="chat" className="mx-auto w-full max-w-[1440px] flex-1 px-8">
        <ChatView />
      </main>

    </div>
  )
}

export default App
