import { useEffect, useRef } from "react"

/**
 * Fixed, full-screen layer of soft colored glows that drift toward the cursor
 * with eased parallax. Sits behind all app content (pointer-events: none).
 */
export default function InteractiveBackground() {
  const layerRef = useRef(null)
  const orbRefs = useRef([])

  // Target (cursor) and current (eased) positions, normalized -0.5..0.5
  const target = useRef({ x: 0, y: 0 })
  const current = useRef({ x: 0, y: 0 })
  const frame = useRef(0)

  // Each orb has a depth factor so they move at different speeds (parallax)
  const orbs = [
    { color: "var(--color-accent)", size: 560, depth: 1.0, base: { x: 18, y: 22 } },
    { color: "oklch(0.6 0.22 280)", size: 520, depth: 0.6, base: { x: 78, y: 30 } },
    { color: "var(--color-risk-low)", size: 440, depth: 1.4, base: { x: 30, y: 78 } },
    { color: "oklch(0.7 0.2 330)", size: 480, depth: 0.85, base: { x: 72, y: 74 } },
  ]

  useEffect(() => {
    const handleMove = (e) => {
      target.current = {
        x: e.clientX / window.innerWidth - 0.5,
        y: e.clientY / window.innerHeight - 0.5,
      }
    }
    window.addEventListener("pointermove", handleMove)

    const tick = () => {
      // Ease current position toward target for smooth trailing motion
      current.current.x += (target.current.x - current.current.x) * 0.06
      current.current.y += (target.current.y - current.current.y) * 0.06

      orbRefs.current.forEach((el, i) => {
        if (!el) return
        const depth = orbs[i].depth
        const dx = current.current.x * 120 * depth
        const dy = current.current.y * 120 * depth
        el.style.transform = `translate3d(${dx}px, ${dy}px, 0)`
      })

      frame.current = requestAnimationFrame(tick)
    }
    frame.current = requestAnimationFrame(tick)

    return () => {
      window.removeEventListener("pointermove", handleMove)
      cancelAnimationFrame(frame.current)
    }
  }, [])

  return (
    <div
      ref={layerRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      {orbs.map((orb, i) => (
        <div
          key={i}
          ref={(el) => (orbRefs.current[i] = el)}
          className="absolute rounded-full blur-[90px] will-change-transform animate-float-orb"
          style={{
            width: orb.size,
            height: orb.size,
            left: `${orb.base.x}%`,
            top: `${orb.base.y}%`,
            marginLeft: -orb.size / 2,
            marginTop: -orb.size / 2,
            background: orb.color,
            opacity: 0.42,
            animationDelay: `${i * -3}s`,
          }}
        />
      ))}
    </div>
  )
}
