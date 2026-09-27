import { useEffect, useState } from 'react'
import { fetchFilings } from '../api'
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

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetchFilings(controller.signal)
      .then(data => {
        if (controller.signal.aborted) return
        setFilings(data)
        if (data.length > 0 && (selectedId === null || !data.some(filing => filing.filing_id === selectedId))) {
          onSelect(data[0])
        }
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
    // onSelect is stable from the parent; retry refetches the catalog.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retry])

  if (loading) return <div className="load-message" role="status">Loading verified filings…</div>
  if (error || !filings) {
    return (
      <div className="load-message load-error" role="alert">
        <h2>Filing catalog unavailable</h2>
        <p>{error ?? 'The filing catalog is incomplete.'}</p>
        <button type="button" className="button button-primary" onClick={() => setRetry(value => value + 1)}>
          Try again
        </button>
      </div>
    )
  }

  const selected = filings.find(filing => filing.filing_id === selectedId) ?? filings[0]

  return (
    <div className="selector-panel">
      <div className="selector-topline">
        <span className="eyebrow">Filing</span>
        <span className="case-count">
          {String(filings.findIndex(filing => filing.filing_id === selected.filing_id) + 1).padStart(2, '0')}
          {' / '}
          {String(filings.length).padStart(2, '0')}
        </span>
      </div>
      <label htmlFor="filing-select">Company / filing year</label>
      <select
        id="filing-select"
        value={selected.filing_id}
        onChange={event => {
          const filing = filings.find(candidate => candidate.filing_id === event.target.value)
          if (filing) onSelect(filing)
        }}
      >
        {filings.map(filing => (
          <option key={filing.filing_id} value={filing.filing_id}>
            {filing.company} · {filing.filing_year} ({filing.ticker})
          </option>
        ))}
      </select>
      <p className="selector-context">
        {selected.filing_id} · SEC filing year {selected.filing_year}
      </p>
      <p className="selector-context">
        <a className="inline-link" href={selected.sec_url} target="_blank" rel="noopener noreferrer">
          Official SEC source ↗
        </a>
      </p>
    </div>
  )
}
