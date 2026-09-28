import type { Verdict } from './types'

export const eyebrow = 'text-[#55877b] text-[.7rem] font-extrabold tracking-[.15em] leading-[1.4] uppercase'

export const inlineLink = 'text-[#246a61] text-[.84rem] font-[750] decoration-[1px]'

export const button = 'inline-flex min-h-12 items-center justify-between gap-7 rounded border border-transparent ' +
  'px-[18px] py-3 text-[.83rem] font-[750] no-underline transition-[background,transform] duration-200 ' +
  'hover:-translate-y-0.5 motion-reduce:transition-none'

export const primaryButton = `${button} bg-[#d8c29f] text-[#142436] hover:bg-[#f0d5ab]`

export const quietButton = `${button} border-[#60727c] bg-transparent text-[#f5f2ea] hover:bg-[#27394a]`

export const sectionHeading = 'mb-6 flex items-end justify-between gap-6 max-[760px]:block'

export const sectionTitle = 'm-0 font-display text-[clamp(2rem,3.4vw,2.7rem)] font-normal'

export const sectionCaption = 'm-0 max-w-[330px] text-right text-[.8rem] leading-[1.6] text-[#65737b] ' +
  'max-[760px]:mt-3 max-[760px]:text-left'

export const explorerGrid = 'grid grid-cols-[260px_minmax(0,1fr)] items-start gap-[18px] ' +
  'max-[1000px]:grid-cols-[220px_minmax(0,1fr)] max-[760px]:grid-cols-1'

export const caseContent = 'grid min-w-0 gap-[18px]'

export const panel = 'min-w-0 rounded-[5px] border border-[#dce2dc] bg-white'

export const answerPanel = `${panel} p-8 max-[460px]:p-[19px]`

export const selectorContext = 'mt-[14px] mb-0 font-code text-[.65rem] leading-[1.6] ' +
  'text-[#8b9794] [overflow-wrap:anywhere]'

export const selectorPanel = `${panel} sticky top-5 p-[23px] max-[760px]:static`

export const selectorTopline = 'flex items-center justify-between gap-[10px]'

export const selectorLabel = 'mt-7 mb-[9px] block text-[.78rem] font-[760]'

export const selectorControl = 'min-h-[46px] w-full rounded-[3px] border border-[#bfcac4] bg-[#f9faf7] ' +
  'py-[9px] pr-[31px] pl-[11px] text-[.77rem] text-[#1d3032]'

export const caseCount = 'font-code text-[.72rem] text-[#687878]'

export const loadMessage = 'my-[74px] border border-[#d8deda] bg-white p-[34px] text-[#4b615f]'

export const loadErrorTitle = 'font-display font-normal'

export const badge = 'inline-flex w-max max-w-full items-center rounded-[3px] px-[10px] py-[7px] ' +
  'text-[.7rem] font-extrabold tracking-[.035em] uppercase'

const verdictColors = {
  pass: 'bg-[#e1f2ea] text-[#196457]',
  partial: 'bg-[#fff1d9] text-[#855721]',
  incorrect: 'bg-[#fde7e1] text-[#a14335]',
  unreviewed: 'bg-[#eaeef0] text-[#59636b]',
}

export function verdictBadge(verdict: Verdict): string {
  return `${badge} ${verdictColors[verdict ?? 'unreviewed']}`
}

export const panelHeading = 'mb-[30px] flex items-start justify-between gap-[25px] max-[460px]:flex-col'

export const panelTitle = 'm-0 max-w-[650px] font-display text-[clamp(1.45rem,2.4vw,2rem)] ' +
  'leading-[1.3] font-normal'

export const answerText = 'm-0 text-[.86rem] leading-[1.75] whitespace-pre-wrap [overflow-wrap:anywhere]'
