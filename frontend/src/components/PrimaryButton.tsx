import type { ComponentProps } from 'react'

export function PrimaryButton({ className = '', children, ...props }: ComponentProps<'button'>) {
  return (
    <button {...props} className={`inline-flex min-h-12 items-center justify-between gap-7 rounded border
      border-transparent bg-[#d8c29f] px-[18px] py-3 font-sans text-[.83rem] font-[750] text-[#142436]
      transition-[background,transform] duration-200 hover:-translate-y-0.5 hover:bg-[#f0d5ab]
      motion-reduce:transition-none ${className}`}>
      {children}
    </button>
  )
}
