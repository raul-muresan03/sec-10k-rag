export function ChunkText({ text, unwrapped }: { text: string; unwrapped: boolean }) {
  if (!unwrapped) return <pre className="chunk-text">{text}</pre>
  return (
    <div className="chunk-text table-layout">
      {text.split('\n').map((line, index) => {
        const first = line.indexOf('|')
        const last = line.lastIndexOf('|')
        return (
          <div className="source-line" key={index}>
            {first >= 0 && last > first ? (
              <>
                {line.slice(0, first) !== '' && <span>{line.slice(0, first)}</span>}
                <span className="source-table-row">{line.slice(first, last + 1)}</span>
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
