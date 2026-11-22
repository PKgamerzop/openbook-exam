import { describe, expect, it } from 'vitest'
import { calculate } from './Calculator'

describe('scientific calculator', () => {
  it('honors precedence, parentheses and right-associative powers', () => {
    expect(calculate('-2^2 + (3+2)*4', true)).toBe(16)
    expect(calculate('2^3^2', true)).toBe(512)
  })
  it('uses the chosen angle units and handles scientific operations', () => {
    expect(calculate('sin(30) + sqrt(9) + log(100) + ln(e)', true)).toBeCloseTo(6.5)
    expect(calculate('cos(pi)', false)).toBeCloseTo(-1)
  })
  it('rejects invalid and undefined expressions', () => {
    for (const input of ['1/0', 'sqrt(-1)', 'tan(90)', '(2+3', 'alert("x")']) {
      expect(() => calculate(input, true)).toThrow()
    }
  })
})
