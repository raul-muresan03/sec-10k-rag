import type { FilingSummary } from '../api'

interface Props {
  status: FilingSummary['status']
  starting: boolean
  requestFailed: boolean
  operatorOnly: boolean
  refreshFailed: boolean
  onRetry: () => void
  onRefresh: () => void
}

function progressMessage(status: FilingSummary['status']): string {
  if (status === 'queued') return 'Waiting to open this filing…'
  if (status === 'downloading') return 'Getting the filing from SEC.gov…'
  if (status === 'waiting_for_models' || status === 'indexing') {
    return 'Getting this filing ready for questions… This may take a while.'
  }
  return 'Opening this filing…'
}

export function FilingPreparationNotice({
  status, starting, requestFailed, operatorOnly, refreshFailed, onRetry, onRefresh,
}: Props) {
  if (status === 'ready') return null

  if (operatorOnly) {
    return (
      <div className="mt-4 text-[.76rem] leading-[1.6] text-[#5c7065]" aria-live="polite">
        <p className="m-0">New filings are prepared by the operator. This catalog is read-only.</p>
      </div>
    )
  }

  const failed = status === 'failed' || requestFailed
  const checkingFailed = refreshFailed && status !== 'unprepared'
  const progress = starting ? 'Opening this filing…' : progressMessage(status)

  return (
    <div className="mt-4 text-[.76rem] leading-[1.6] text-[#5c7065]" aria-live="polite">
      {!starting && (failed || checkingFailed) ? (
        <div role="alert">
          <p className="mt-0 mb-3 text-[#9b583e]">
            {failed ? 'We couldn’t open this filing. Please try again.'
              : 'We couldn’t check this filing right now. Please check again.'}
          </p>
          <button type="button" className="rounded-md border border-[#c7d9ca] bg-white px-3 py-2
            font-sans text-[.75rem] font-semibold text-[#2e6956] hover:bg-[#edf5ee]"
            onClick={failed ? onRetry : onRefresh}>
            {failed ? 'Try again' : 'Check again'}
          </button>
        </div>
      ) : (
        <p className="m-0" role="status">{progress}</p>
      )}
    </div>
  )
}
