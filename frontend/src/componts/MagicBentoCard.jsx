import { useRef, useCallback } from 'react'

/**
 * MagicBentoCard — Card with mouse-tracking radial border glow.
 * Apply className like bento/bento-accent/bento-dark on top for theming.
 */
const MagicBentoCard = ({ children, className = '', style = {}, ...rest }) => {
  const cardRef = useRef(null)

  const handleMouseMove = useCallback((e) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    cardRef.current.style.setProperty('--glow-x', `${x}px`)
    cardRef.current.style.setProperty('--glow-y', `${y}px`)
    cardRef.current.style.setProperty('--glow-intensity', '1')
  }, [])

  const handleMouseLeave = useCallback(() => {
    if (!cardRef.current) return
    cardRef.current.style.setProperty('--glow-intensity', '0')
  }, [])

  return (
    <div
      ref={cardRef}
      className={`magic-bento cursor-target ${className}`}
      style={{
        '--glow-x': '50%',
        '--glow-y': '50%',
        '--glow-intensity': '0',
        '--glow-radius': '250px',
        ...style,
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      {...rest}
    >
      {children}
      {/* Glow border overlay */}
      <div className="magic-bento__glow" />
    </div>
  )
}

export default MagicBentoCard
