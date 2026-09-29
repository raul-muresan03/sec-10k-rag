import type { FilingSummary } from '../api'

interface Props {
  status: FilingSummary['status']
  starting: boolean
  requestFailed: boolean
  refreshFailed: boolean
  onRetry: () => void
  onRefresh: () => void
}

export function FilingPreparationNotice({
  status, starting, requestFailed, refreshFailed, onRetry, onRefresh,
}: Props) {
  if (status === 'ready') return null

  const failed = status === 'failed' || requestFailed
  const checkingFailed = refreshFailed && status !== 'unprepared'

  return (
    <div className="mt-4 text-[.76rem] leading-[1.6] text-[#5c7065]" aria-live="polite">
      {starting ? (
        <p className="m-0" role="status">Opening this filing… This may take a while.</p>
      ) : failed || checkingFailed ? (
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
        <p className="m-0" role="status">Opening this filing… This may take a while.</p>
      )}
    </div>
  )
}
