interface Props {
  id: string
  eyebrow: string
  title: string
  caption: string
}

export function SectionHeading({ id, eyebrow, title, caption }: Props) {
  return (
    <div className="mb-6 flex items-end justify-between gap-6">
      <div>
        <p className="mb-2 text-[.7rem] leading-[1.4] font-extrabold tracking-[.15em] text-[#55877b] uppercase">
          {eyebrow}
        </p>
        <h2 id={id} className="m-0 font-display text-[clamp(2rem,3.4vw,2.7rem)] font-normal">
          {title}
        </h2>
      </div>
      <p className="m-0 max-w-[330px] text-right text-[.8rem] leading-[1.6] text-[#65737b]">
        {caption}
      </p>
    </div>
  )
}
