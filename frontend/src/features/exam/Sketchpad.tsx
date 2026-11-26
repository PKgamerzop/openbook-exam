import { useRef, useState, type PointerEvent } from 'react'

type Point = { x: number; y: number }

function draw(context: CanvasRenderingContext2D, from: Point, to: Point) {
  context.strokeStyle = '#284965'
  context.lineWidth = 3
  context.lineCap = 'round'
  context.beginPath()
  context.moveTo(from.x, from.y)
  context.lineTo(to.x, to.y)
  context.stroke()
}

export function Sketchpad({ disabled }: { disabled: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const strokes = useRef<Point[][]>([])
  const active = useRef<number | null>(null)
  const [count, setCount] = useState(0)

  function point(event: PointerEvent<HTMLCanvasElement>): Point {
    const target = event.currentTarget
    const bounds = target.getBoundingClientRect()
    return {
      x: (event.clientX - bounds.left) * target.width / bounds.width,
      y: (event.clientY - bounds.top) * target.height / bounds.height,
    }
  }

  function redraw() {
    const target = canvas.current!
    const context = target.getContext('2d')
    if (context) {
      context.clearRect(0, 0, target.width, target.height)
      for (const stroke of strokes.current) {
        stroke.forEach((p, index) => draw(context, stroke[index - 1] ?? { ...p, x: p.x + .1 }, p))
      }
    }
    setCount(strokes.current.length)
  }

  return (
    <div className="sketchpad">
      <p className="muted">Use a mouse, pen or touch to draw. Sketches clear when you leave or reload the attempt.</p>
      <canvas ref={canvas} width={1000} height={700} aria-label="Sketch canvas"
        onPointerDown={(event) => {
          if (disabled || event.button !== 0 || active.current !== null) return
          event.currentTarget.setPointerCapture(event.pointerId)
          active.current = event.pointerId
          const p = point(event)
          strokes.current.push([p])
          const context = event.currentTarget.getContext('2d')
          if (context) draw(context, { ...p, x: p.x + .1 }, p)
          setCount(strokes.current.length)
        }}
        onPointerMove={(event) => {
          if (disabled || active.current !== event.pointerId) return
          const stroke = strokes.current.at(-1)!
          const p = point(event)
          const context = event.currentTarget.getContext('2d')
          if (context) draw(context, stroke.at(-1)!, p)
          stroke.push(p)
        }}
        onLostPointerCapture={() => { active.current = null }}
      />
      <div className="question-actions">
        <button className="button-secondary" disabled={disabled || !count} onClick={() => {
          if (active.current !== null) return
          strokes.current.pop()
          redraw()
        }}>Undo stroke</button>
        <button className="button-quiet" disabled={disabled || !count} onClick={() => {
          if (active.current !== null) return
          strokes.current = []
          redraw()
        }}>Clear sketch</button>
      </div>
    </div>
  )
}
