export type Question = {
  stem: string
  options: string[]
  correct: number
  topics: string[]
  objectives: string[]
}
export type Draft = {
  title: string
  instructions: string
  rules: string
  reference_versions?: number[]
  pre_release?: boolean
  calculator: boolean
  opens_at: string | null
  closes_at: string | null
  duration: number | null
  students: number[]
  questions: Question[]
}
export type Exam = {
  id: number
  draft: Draft
  edit_number: number
  published_number: number | null
  published?: Draft
  frozen?: boolean
}
export type Course = { id: number; name: string }
export type Roster = Course & {
  students: { id: number; username: string }[]
  labels: { kind: string; name: string }[]
}

export function localTime(iso: string | null) {
  if (!iso) return ''
  const date = new Date(iso)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16)
}

export function moveQuestion(items: Question[], index: number, delta: number) {
  const result = [...items]
  const target = index + delta
  if (
    index < 0 ||
    index >= items.length ||
    target < 0 ||
    target >= items.length
  )
    return result
  result.splice(target, 0, result.splice(index, 1)[0])
  return result
}
