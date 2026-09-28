import { useEffect, useRef, useState } from 'react'
import { fetchFilings, prepareFiling } from '../api'
import type { FilingSummary } from '../api'
import {
  caseCount, eyebrow, inlineLink, loadErrorTitle, loadMessage, primaryButton, selectorContext,
  selectorControl, selectorLabel, selectorPanel, selectorTopline,
} from '../ui'

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
        update(data)
      })
      .catch(reason => {
        if (controller.signal.aborted) return
        if (reason instanceof Error && reason.name === 'AbortError') return
        setError(reason instanceof Error ? reason.message : 'The filing catalog could not be loaded.')
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
      void fetchFilings(controller.signal).then(update).catch(reason => {
        if (controller.signal.aborted) return
        setPrepareError(reason instanceof Error ? reason.message : 'Could not refresh preparation status.')
      })
    }, 4000)
    return () => { controller.abort(); clearInterval(timer) }
    // update reads the latest selectionRef without restarting the interval on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  const prepare = async (selected: FilingSummary) => {
    if (starting !== null) return
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
    } catch (reason) {
      setPrepareError(reason instanceof Error ? reason.message : 'Could not start preparation.')
    } finally {
      setStarting(null)
    }
  }

  if (loading) return <div className={loadMessage} role="status">Loading verified filings…</div>
  if (error || !filings) {
    return (
      <div className={loadMessage} role="alert">
        <h2 className={loadErrorTitle}>Filing catalog unavailable</h2>
        <p>{error ?? 'The filing catalog is incomplete.'}</p>
        <button type="button" className={`${primaryButton} mt-[10px]`}
          onClick={() => setRetry(value => value + 1)}>
          Try again
        </button>
      </div>
    )
  }

  const selected = filings.find(filing => filing.filing_id === selectedId) ?? filings[0]

  return (
    <div className={selectorPanel}>
      <div className={selectorTopline}>
        <span className={eyebrow}>Filing</span>
        <span className={caseCount}>
          {String(filings.findIndex(filing => filing.filing_id === selected.filing_id) + 1).padStart(2, '0')}
          {' / '}
          {String(filings.length).padStart(2, '0')}
        </span>
      </div>
      <label className={selectorLabel} htmlFor="filing-select">Company / filing year</label>
      <select
        id="filing-select"
        className={selectorControl}
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
      <p className={selectorContext}>
        {selected.filing_id} · SEC filing year {selected.filing_year}
      </p>
      <p className={selectorContext}>
        <a className={inlineLink} href={selected.sec_url} target="_blank" rel="noopener noreferrer">
          Official SEC source ↗
        </a>
      </p>
      <div className="mt-[22px] border-t border-[#e4e9e5] pt-4" aria-live="polite">
        {selected.status === 'ready' ? (
          <p className="mb-3 text-[.78rem] leading-normal text-[#49665d] [overflow-wrap:anywhere]">
            Ready to chat · verified source and index
          </p>
        ) : selected.status === 'unprepared' || selected.status === 'failed' ? (
          <>
            <p className="mb-3 text-[.78rem] leading-normal text-[#49665d] [overflow-wrap:anywhere]">
              {selected.status === 'failed' ? selected.detail : 'This filing has not been prepared yet.'}
            </p>
            <button type="button" className={`${primaryButton} w-full justify-center disabled:cursor-not-allowed
              disabled:opacity-60`} disabled={starting !== null}
              onClick={() => void prepare(selected)}>
              {starting === selected.filing_id ? 'Starting…'
                : selected.status === 'failed' ? 'Retry preparation' : 'Prepare filing'}
            </button>
          </>
        ) : (
          <p className="mb-3 text-[.78rem] leading-normal text-[#49665d] [overflow-wrap:anywhere]"
            role="status">{selected.status === 'queued' ? 'Queued' : selected.status === 'waiting_for_models'
              ? 'Waiting for embedding model' : selected.status === 'downloading' ? 'Downloading from SEC'
                : 'Building the index'}… This can take a while on CPU.</p>
        )}
        {prepareError && <p className="mb-3 text-[.78rem] leading-normal text-[#9b583e]"
          role="alert">{prepareError}</p>}
      </div>
    </div>
  )
}
