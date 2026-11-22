import { useState } from 'react'

export function calculate(expression: string, degrees: boolean): number {
  if (expression.length > 160) throw new Error('Expression is too long.')
  const source = expression.replace(/\s+/g, '')
  const tokens = source.match(/\d+(?:\.\d*)?|\.\d+|[a-z]+|[()+*/^-]/g) ?? []
  if (tokens.join('') !== source) throw new Error('Invalid expression.')
  const input = tokens.values()
  let token = input.next().value
  function consume(expected: string) {
    if (token !== expected) return false
    token = input.next().value
    return true
  }
  function group(): number {
    if (!consume('(')) throw new Error('Expected an opening parenthesis.')
    const value = sum()
    if (!consume(')')) throw new Error('Expected a closing parenthesis.')
    return value
  }
  function atom(): number {
    if (token === '(') return group()
    const part = token
    token = input.next().value
    if (part && /^\d|^\./.test(part)) return Number(part)
    if (part === 'pi') return Math.PI
    if (part === 'e') return Math.E
    if (!part || !['sqrt', 'log', 'ln', 'sin', 'cos', 'tan'].includes(part))
      throw new Error('Expected a number or function.')
    const n = group()
    const angle = degrees ? (n * Math.PI) / 180 : n
    switch (part) {
      case 'sqrt':
        return Math.sqrt(n)
      case 'log':
        return Math.log10(n)
      case 'ln':
        return Math.log(n)
      case 'sin':
        return Math.sin(angle)
      case 'cos':
        return Math.cos(angle)
      default:
        if (Math.abs(Math.cos(angle)) < 1e-14)
          throw new Error('Tangent is undefined.')
        return Math.tan(angle)
    }
  }
  function signed(): number {
    if (consume('-')) return -signed()
    if (consume('+')) return signed()
    const base = atom()
    return consume('^') ? base ** signed() : base
  }
  function product(): number {
    let n = signed()
    for (;;) {
      if (consume('*')) n *= signed()
      else if (consume('/')) n /= signed()
      else return n
    }
  }
  function sum(): number {
    let n = product()
    for (;;) {
      if (consume('+')) n += product()
      else if (consume('-')) n -= product()
      else return n
    }
  }
  const value = sum()
  if (token !== undefined || !Number.isFinite(value))
    throw new Error('Invalid or undefined result.')
  return value
}

export function Calculator() {
  const [expression, setExpression] = useState('')
  const [degrees, setDegrees] = useState(true)
  const [result, setResult] = useState('')
  return (
    <details>
      <summary>Scientific calculator</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          try {
            setResult(String(calculate(expression, degrees)))
          } catch (error) {
            setResult((error as Error).message)
          }
        }}
      >
        <label>
          Expression
          <input
            value={expression}
            maxLength={160}
            onChange={(e) => setExpression(e.target.value)}
          />
        </label>
        <p>Functions: sqrt, log, ln, sin, cos, tan. Powers use ^.</p>
        <label>
          Angle units
          <select
            value={degrees ? 'degrees' : 'radians'}
            onChange={(e) => setDegrees(e.target.value === 'degrees')}
          >
            <option value="degrees">Degrees</option>
            <option value="radians">Radians</option>
          </select>
        </label>
        <button>Calculate</button>
        <button
          type="button"
          onClick={() => setExpression(expression.slice(0, -1))}
        >
          Backspace
        </button>
        <button
          type="button"
          onClick={() => {
            setExpression('')
            setResult('')
          }}
        >
          Clear
        </button>
        <output aria-live="polite">{result}</output>
      </form>
    </details>
  )
}
