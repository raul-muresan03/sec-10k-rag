import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  role: 'alert' | 'status'
}

export function Notice({ children, role }: Props) {
  return (
    <div className="my-[74px] border border-[#d8deda] bg-white p-[34px] text-[#4b615f]" role={role}>
      {children}
    </div>
  )
}
