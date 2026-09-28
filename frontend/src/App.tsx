import { useState } from 'react'
import { ChatView } from './components/ChatView'
import { EvaluationView } from './views/EvaluationView'
import { primaryButton, quietButton } from './ui'

const REPO_URL = 'https://github.com/raul-muresan03/sec-rag-tool'

type View = 'chat' | 'evaluation'

function App() {
  const [view, setView] = useState<View>('chat')

  const select = (next: View) => (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    setView(next)
  }

  return (
    <div className="overflow-hidden">
      <header className="mx-auto flex min-h-[78px] w-[calc(100%-64px)] max-w-[1180px] items-center
        justify-between border-b border-[#314151] text-[#eeeae1] max-[760.01px]:min-h-[68px]
        max-[760.01px]:w-[calc(100%-32px)] max-[760.01px]:max-w-[550px] max-[760.01px]:flex-wrap
        max-[760.01px]:gap-3 max-[760.01px]:py-[14px]">
        <a className="inline-flex items-center gap-[14px] text-[.88rem] font-[750] no-underline"
          href="#top" aria-label="SEC RAG Evidence Lab home">
          <span className="grid size-9 place-items-center rounded-[5px] border border-[#bca983]
            font-display text-[.96rem] text-[#d9c5a1]" aria-hidden="true">
            S<span className="-mx-[2px] text-[#78aa9d]">·</span>R
          </span>
          <span className="max-[460.01px]:text-[.74rem]">SEC RAG <em className="not-italic text-[#9aadaf]">/</em>
            {' '}Evidence Lab</span>
        </a>
        <nav className="flex items-center gap-[29px] text-[.79rem] font-[650]
          max-[760.01px]:w-full max-[760.01px]:justify-between max-[760.01px]:gap-3
          max-[460.01px]:text-[.7rem]"
          aria-label="Primary navigation">
          <a className="text-[#ced7d6] no-underline hover:text-white max-[760.01px]:whitespace-nowrap"
            href="#chat" aria-current={view === 'chat' ? 'page' : undefined} onClick={select('chat')}>Chat</a>
          <a
            className="text-[#ced7d6] no-underline hover:text-white max-[760.01px]:whitespace-nowrap"
            href="#evaluation"
            aria-current={view === 'evaluation' ? 'page' : undefined}
            onClick={select('evaluation')}
          >
            Evaluation
          </a>
          <a className="text-[#ced7d6] no-underline hover:text-white max-[760.01px]:whitespace-nowrap"
            href={REPO_URL} target="_blank" rel="noopener noreferrer">
            Source code <span aria-hidden="true">↗</span>
          </a>
        </nav>
      </header>

      <main id="top">
        <section className="mx-auto grid w-[calc(100%-64px)] max-w-[1180px] grid-cols-[1.3fr_.7fr]
          items-center gap-20 pt-[96px] pb-[110px] max-[1000.01px]:gap-10 max-[760.01px]:w-[calc(100%-32px)]
          max-[760.01px]:max-w-[550px] max-[760.01px]:grid-cols-1 max-[760.01px]:gap-9
          max-[760.01px]:pt-[65px] max-[760.01px]:pb-[75px]" aria-labelledby="hero-title">
          <div className="max-w-[660px]">
            <div className="flex items-center gap-[11px] text-[.75rem] tracking-[.12em] text-[#bad0c9]
              uppercase max-[760.01px]:flex-wrap">
              <span className="inline-block size-[7px] shrink-0 rounded-full bg-[#8dc2a8]
                shadow-[0_0_0_4px_#8dc2a822]" /> Live answers over verified 10-K filings
              <span className="text-[#8c9fa6]">—</span> v1
            </div>
            <h1 id="hero-title" className="mt-6 mb-5 font-display text-[clamp(3.8rem,6.7vw,6.9rem)]
              leading-[1.04] font-normal text-[#f6f4ed] max-[1000.01px]:text-[clamp(3.5rem,7vw,5.4rem)]
              max-[760.01px]:text-[clamp(3.75rem,12vw,5.2rem)] max-[460.01px]:text-[3.55rem]">
              Evidence <i className="font-normal text-[#d5bc90]">before</i><br />answers.
            </h1>
            <p className="max-w-[560px] text-[1.02rem] leading-[1.8] text-[#bfcbd0]">
              Ask a question about one verified filing and read the generated answer next to the
              retrieved passages. The saved evaluation replay lives under Evaluation.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a className={`${primaryButton} max-[460.01px]:w-full`} href="#chat" onClick={select('chat')}>
                Ask a question <span aria-hidden="true">↗</span>
              </a>
              <a className={`${quietButton} max-[460.01px]:w-full`} href="#evaluation" onClick={select('evaluation')}>
                Inspect saved evaluation <span aria-hidden="true">↗</span>
              </a>
            </div>
          </div>
          <aside className="rotate-[1.3deg] rounded-lg border border-[#42545e] bg-[#192b3b] p-[26px]
            shadow-[14px_18px_0_#ffffff08] max-[760.01px]:max-w-[430px] max-[760.01px]:rotate-0"
            aria-label="How this app works">
            <div className="flex justify-between font-code text-[.68rem] tracking-[.08em] text-[#a6b7ba]">
              <span>LIVE / 001</span><span>SEC · 10-K</span>
            </div>
            <div className="mt-[54px] mb-[38px] flex items-center gap-3 font-display text-[2.3rem]
              text-[#dbccad] max-[760.01px]:my-[22px]" aria-hidden="true">
              <span>?</span><span className="font-code text-[1.4rem] text-[#70a595]">→</span><span>§</span>
              <span className="font-code text-[1.4rem] text-[#70a595]">→</span><span>A</span>
            </div>
            <h2 className="font-display text-[1.65rem] font-normal text-[#f5f1e7]">Live filing chat</h2>
            <p className="text-[.86rem] leading-[1.7] text-[#b8c6c9]">
              Choose a filing, ask in your own words, and inspect the answer with its evidence.
            </p>
            <div className="mt-[25px] mb-[21px] h-px bg-[#40535d]" />
            <div className="flex items-center gap-[14px] font-code text-[.65rem] tracking-[.08em] text-[#a6b7ba]">
              <span className="inline-block size-[7px] shrink-0 rounded-full bg-[#8dc2a8]
                shadow-[0_0_0_4px_#8dc2a822]" /> Live inference · Independent questions
            </div>
          </aside>
        </section>

        <div className="bg-[#f6f5f1] pt-px pb-[90px]">
          <div className="mx-auto w-[calc(100%-64px)] max-w-[1180px] max-[760.01px]:w-[calc(100%-32px)]
            max-[760.01px]:max-w-[550px]">
            {view === 'chat' ? (
              <ChatView />
            ) : (
              <EvaluationView />
            )}
          </div>
        </div>
      </main>
      <footer className="mx-auto flex min-h-[95px] w-[calc(100%-64px)] max-w-[1180px] items-center
        justify-between gap-5 text-[.74rem] text-[#adbfc2] max-[760.01px]:w-[calc(100%-32px)]
        max-[760.01px]:max-w-[550px] max-[760.01px]:flex-wrap max-[760.01px]:py-[25px]">
        <span>SEC RAG / Evidence Lab</span>
        <span>Built to make failure visible.</span>
        <a className="text-[#e3d0ac] underline-offset-4" href={REPO_URL} target="_blank"
          rel="noopener noreferrer">View on GitHub ↗</a>
      </footer>
    </div>
  )
}

export default App
