export function ChunkText({ text, unwrapped }: { text: string; unwrapped: boolean }) {
  if (!unwrapped) return <pre className="m-0 px-0 pt-[14px] pb-1 font-code text-[.71rem] leading-[1.65]
    text-[#3f5151] whitespace-pre-wrap [overflow-wrap:anywhere]">{text}</pre>
  return (
    <div className="m-0 px-0 pt-[14px] pb-1 font-code text-[.71rem] leading-[1.65]
      text-[#3f5151] whitespace-pre-wrap [overflow-wrap:anywhere]">
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
