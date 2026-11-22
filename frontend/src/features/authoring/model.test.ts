import { expect, it } from 'vitest'
import { localTime, moveQuestion } from './model'

it('moves a complete MCQ with its key and topics without modifying the draft', () => {
  const one = {
    stem: 'First',
    options: ['A', 'B'],
    correct: 1,
    topics: ['T'],
    objectives: [],
  }
  const two = { ...one, stem: 'Second', correct: 0 }
  const questions = [one, two]
  expect(moveQuestion(questions, 1, -1)).toEqual([two, one])
  expect(moveQuestion(questions, 0, -1)).toEqual(questions)
  expect(questions).toEqual([one, two])
})
it('round trips a scheduled local minute and accepts an unset draft time', () => {
  expect(localTime(null)).toBe('')
  const instant = new Date(2026, 2, 15, 9, 30)
  expect(new Date(localTime(instant.toISOString())).getTime()).toBe(
    instant.getTime(),
  )
})
