import { useEffect, useRef, useState } from 'react'
import { fetchFilings, prepareFiling } from '../api'
import type { FilingSummary } from '../api'

interface Props {
  selectedId: string | null
  onSelect: (filing: FilingSummary) => void
}

export function FilingSelector({ selectedId, onSelect }: Props) {
  const [filings, setFilings] = useState<FilingSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)
  const [starting, setStarting] = useState<string | null>(null)
  const [prepareError, setPrepareError] = useState<string | null>(null)
  const attemptedRef = useRef(new Set<string>())
  const preparingRef = useRef(new Set<string>())
  const selectionRef = useRef({ selectedId, onSelect })
  selectionRef.current = { selectedId, onSelect }

  const update = (data: FilingSummary[]) => {
    setFilings(data)
    const current = selectionRef.current
    const selected = data.find(filing => filing.filing_id === current.selectedId) ?? data[0]
    if (selected) current.onSelect(selected)
  }

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetchFilings(controller.signal)
      .then(data => {
        if (controller.signal.aborted) return
        setPrepareError(null)
        update(data)
      })
      .catch(reason => {
        if (controller.signal.aborted) return
        if (reason instanceof Error && reason.name === 'AbortError') return
        setError('We couldn’t load the available filings. Please try again.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
    // The current selection callback is read from selectionRef during refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retry])

  const active = filings?.some(filing =>
    ['queued', 'downloading', 'waiting_for_models', 'indexing'].includes(filing.status),
  ) ?? false
  useEffect(() => {
    if (!active) return
    const controller = new AbortController()
    const timer = setInterval(() => {
      void fetchFilings(controller.signal).then(data => {
        if (controller.signal.aborted) return
        setPrepareError(null)
        update(data)
      }).catch(() => {
        if (controller.signal.aborted) return
        setPrepareError('We couldn’t refresh this filing. Please try again.')
      })
    }, 4000)
    return () => { controller.abort(); clearInterval(timer) }
    // update reads the latest selectionRef without restarting the interval on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  const prepare = async (selected: FilingSummary) => {
    if (preparingRef.current.has(selected.filing_id)) return
    preparingRef.current.add(selected.filing_id)
    setStarting(selected.filing_id)
    setPrepareError(null)
    try {
      const result = await prepareFiling(selected.filing_id)
      setFilings(previous => previous?.map(filing =>
        filing.filing_id === selected.filing_id ? { ...filing, ...result } : filing,
      ) ?? null)
      if (selectionRef.current.selectedId === selected.filing_id) {
        selectionRef.current.onSelect({ ...selected, ...result })
      }
    } catch {
      if (selectionRef.current.selectedId === selected.filing_id) {
        setPrepareError('We couldn’t open this filing. Please try again.')
      }
    } finally {
      preparingRef.current.delete(selected.filing_id)
      setStarting(previous => previous === selected.filing_id ? null : previous)
    }
  }

  const selected = filings?.find(filing => filing.filing_id === selectedId) ?? filings?.[0]

  useEffect(() => {
    if (!selected || selected.status !== 'unprepared' || attemptedRef.current.has(selected.filing_id)) return
    attemptedRef.current.add(selected.filing_id)
    void prepare(selected)
    // Prepare once on selection; explicit retry remains available after failure.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.filing_id, selected?.status])

  if (loading) return <p className="mt-0 text-[.8rem] text-[#62746e]" role="status">Finding filings…</p>
  if (error || !filings) {
    return (
      <div role="alert" className="rounded-lg border border-[#e8d4c9] bg-white p-4">
        <p className="mt-0 mb-3 text-[.8rem] leading-[1.6] text-[#8d4e3c]">
          {error ?? 'We couldn’t load the available filings. Please try again.'}
        </p>
        <button type="button" className="rounded-md border border-[#d8bcae] bg-[#fcf5f1]
          px-4 py-2 font-sans text-[.78rem] font-semibold text-[#854b3b] hover:bg-[#f7ebe5]"
          onClick={() => setRetry(value => value + 1)}>Try again</button>
      </div>
    )
  }

  if (!selected) return null

  return (
    <div className="min-w-0">
      <label className="mb-2 block text-[.74rem] font-semibold text-[#405d53]" htmlFor="filing-select">
        Company · filing year
      </label>
      <select
        id="filing-select"
        className="min-h-12 w-full rounded-lg border border-[#bdd0c4] bg-white px-3 py-2 font-sans
          text-[.82rem] text-[#1d3032] hover:border-[#82ad95]"
        value={selected.filing_id}
        onChange={event => {
          const filing = filings.find(candidate => candidate.filing_id === event.target.value)
          if (filing) {
            setPrepareError(null)
            onSelect(filing)
          }
        }}
      >
        {filings.map(filing => (
          <option key={filing.filing_id} value={filing.filing_id}>
            {filing.company} · {filing.filing_year} ({filing.ticker})
          </option>
        ))}
      </select>
      <div className="mt-5 rounded-lg border border-[#d9e4dc] bg-white p-4" aria-live="polite">
        <p className="mt-0 mb-2 text-[.8rem] font-semibold text-[#243d37]">
          {selected.company} <span className="font-normal text-[#697b73]">({selected.ticker})</span>
        </p>
        <p className="mt-0 mb-3 text-[.74rem] text-[#6c7e76]">Annual filing · {selected.filing_year}</p>
        <a className="text-[.74rem] font-semibold text-[#2d6d5f] underline-offset-4 hover:underline"
          href={selected.sec_url} target="_blank" rel="noopener noreferrer">
          View original on SEC.gov ↗
        </a>
      </div>
      <div className="mt-4 text-[.76rem] leading-[1.6] text-[#5c7065]" aria-live="polite">
        {selected.status === 'ready' ? (
          <p className="mt-0 mb-0 flex items-center gap-2">
            <span className="size-2 rounded-full bg-[#62a67d]" aria-hidden="true" /> Ready for questions
          </p>
        ) : selected.status === 'failed' || prepareError ? (
          <>
            <p className="mt-0 mb-3 text-[#9b583e]" role="alert">
              We couldn’t open this filing. Please try again.
            </p>
            <button type="button" className="rounded-md border border-[#c7d9ca] bg-white px-3 py-2
              font-sans text-[.75rem] font-semibold text-[#2e6956] hover:bg-[#edf5ee]"
              disabled={starting === selected.filing_id}
              onClick={() => {
                if (selected.status === 'unprepared' || selected.status === 'failed') void prepare(selected)
                else setRetry(value => value + 1)
              }}>Try again</button>
          </>
        ) : (
          <p className="mt-0" role="status">Opening this filing… This can take a few minutes.</p>
        )}
      </div>
    </div>
  )
}
