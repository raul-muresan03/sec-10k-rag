import { ChatView } from './components/ChatView'

function App() {
  return (
    <div className="overflow-hidden">
      <header className="mx-auto flex min-h-[78px] w-[calc(100%-64px)] max-w-[1180px] items-center
        justify-between border-b border-[#314151] text-[#eeeae1]">
        <a className="inline-flex items-center gap-[14px] text-[.88rem] font-[750]
          text-[#eeeae1] no-underline"
          href="#top" aria-label="SEC 10-K RAG home">
          <span className="text-[#9aadaf]">SEC 10-K RAG</span>
        </a>
        <span className="text-[.8rem] text-[#ced7d6]">Explore SEC annual filings</span>
      </header>

      <main id="top">
        <section className="mx-auto grid w-[calc(100%-64px)] max-w-[1180px] grid-cols-[1.3fr_.7fr]
          items-center gap-20 pt-[96px] pb-[110px]" aria-labelledby="hero-title">
          <div className="max-w-[660px]">
            <h1 id="hero-title" className="mt-6 mb-5 font-display text-[clamp(3.8rem,6.7vw,6.9rem)]
              leading-[1.04] font-normal text-[#f6f4ed]">
              Evidence <i className="font-normal text-[#d5bc90]">before</i><br />answers.
            </h1>
            <p className="mt-0 max-w-[560px] text-[1.02rem] leading-[1.8] text-[#bfcbd0]">
              Choose a company and annual filing, then ask what you want to know.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a className="inline-flex min-h-12 items-center justify-between gap-7 rounded border
                border-transparent bg-[#d8c29f] px-[18px] py-3 text-[.83rem] font-[750] text-[#142436]
                no-underline transition-[background,transform] duration-200 hover:-translate-y-0.5
                hover:bg-[#f0d5ab] motion-reduce:transition-none" href="#chat">
                Ask a question <span aria-hidden="true">↗</span>
              </a>
            </div>
          </div>
        </section>
        <div className="bg-[#f6f5f1] pt-px pb-[90px]">
          <div className="mx-auto w-[calc(100%-64px)] max-w-[1180px]">
            <ChatView />
          </div>
        </div>
      </main>
      <footer className="mx-auto flex min-h-[95px] w-[calc(100%-64px)] max-w-[1180px] items-center
        justify-center gap-5 text-[.74rem] text-[#adbfc2]">
        <span>Built by Raul Mureșan</span>
      </footer>
    </div>
  )
}

export default App
