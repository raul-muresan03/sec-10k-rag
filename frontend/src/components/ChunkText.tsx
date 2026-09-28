import { chunkText } from '../ui'

export function ChunkText({ text, unwrapped }: { text: string; unwrapped: boolean }) {
  if (!unwrapped) return <pre className={chunkText}>{text}</pre>
  return (
    <div className={chunkText}>
      {text.split('\n').map((line, index) => {
        const first = line.indexOf('|')
        const last = line.lastIndexOf('|')
        return (
          <div className="min-h-[1.65em]" key={index}>
            {first >= 0 && last > first ? (
              <>
                {line.slice(0, first) !== '' && <span>{line.slice(0, first)}</span>}
                <span className="block w-max min-w-full whitespace-pre [overflow-wrap:normal]">
                  {line.slice(first, last + 1)}
                </span>
                {line.slice(last + 1) !== '' && <span>{line.slice(last + 1)}</span>}
              </>
            ) : (
              line || ' '
            )}
          </div>
        )
      })}
    </div>
  )
}
