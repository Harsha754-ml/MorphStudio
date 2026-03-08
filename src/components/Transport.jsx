import React, { useEffect, useRef, useCallback } from 'react'
import useStore from '../store/useStore'

const FPS = 30

export default function Transport() {
  const isPlaying = useStore((s) => s.isPlaying)
  const loopPlayback = useStore((s) => s.loopPlayback)
  const currentT = useStore((s) => s.currentT)
  const assets = useStore((s) => s.assets)
  const setPlaying = useStore((s) => s.setPlaying)
  const setLoopPlayback = useStore((s) => s.setLoopPlayback)
  const setCurrentT = useStore((s) => s.setCurrentT)

  const rafRef = useRef(null)
  const lastTimeRef = useRef(null)

  const maxDuration = assets.length > 0
    ? Math.max(...assets.map((a) => a.delay + a.duration))
    : 2

  // Playback RAF loop
  useEffect(() => {
    if (!isPlaying) {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
        lastTimeRef.current = null
      }
      return
    }

    const tick = (ts) => {
      if (lastTimeRef.current === null) {
        lastTimeRef.current = ts
        rafRef.current = requestAnimationFrame(tick)
        return
      }
      const dt = ts - lastTimeRef.current
      lastTimeRef.current = ts

      const tIncrement = dt / (maxDuration * 1000)
      const currentState = useStore.getState()
      let newT = currentState.currentT + tIncrement

      if (newT >= 1.0) {
        if (loopPlayback) {
          newT = newT % 1.0
        } else {
          newT = 1.0
          setCurrentT(newT)
          setPlaying(false)
          return
        }
      }

      setCurrentT(newT)
      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
        lastTimeRef.current = null
      }
    }
  }, [isPlaying, loopPlayback, maxDuration, setCurrentT, setPlaying])

  const handlePlayPause = useCallback(() => {
    if (currentT >= 1.0 && !isPlaying) {
      setCurrentT(0)
    }
    setPlaying(!isPlaying)
  }, [isPlaying, currentT, setPlaying, setCurrentT])

  const handleRewind = useCallback(() => {
    setCurrentT(0)
    setPlaying(false)
  }, [setCurrentT, setPlaying])

  const timeDisplay = `${(currentT * maxDuration).toFixed(2)}s`
  const totalDisplay = `${maxDuration.toFixed(2)}s`

  return (
    <div
      style={{
        height: 40,
        minHeight: 40,
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '0 12px',
        background: 'var(--bg-panel)',
        borderTop: '1px solid var(--border-default)',
        borderBottom: '1px solid var(--border-subtle)',
        flexShrink: 0,
      }}
    >
      {/* Rewind button */}
      <button
        className="btn-icon"
        title="Rewind to start"
        onClick={handleRewind}
        style={{ fontSize: 14 }}
      >
        ⏮
      </button>

      {/* Play / Pause */}
      <button
        className={`btn-icon${isPlaying ? ' active' : ''}`}
        title={isPlaying ? 'Pause' : 'Play'}
        onClick={handlePlayPause}
        style={{ fontSize: 14, width: 32, height: 32 }}
      >
        {isPlaying ? '⏸' : '▶'}
      </button>

      {/* Time display */}
      <div
        style={{
          fontFamily: 'JetBrains Mono, Fira Code, monospace',
          fontSize: 12,
          color: 'var(--text-primary)',
          padding: '0 10px',
          minWidth: 120,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
        }}
      >
        <span style={{ color: 'var(--accent)' }}>{timeDisplay}</span>
        <span style={{ color: 'var(--text-dim)' }}>/</span>
        <span style={{ color: 'var(--text-secondary)' }}>{totalDisplay}</span>
      </div>

      {/* Progress scrubber */}
      <div style={{ flex: 1, padding: '0 8px', display: 'flex', alignItems: 'center' }}>
        <div
          style={{
            flex: 1,
            height: 3,
            background: 'var(--bg-raised)',
            borderRadius: 2,
            position: 'relative',
            cursor: 'pointer',
          }}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect()
            const t = (e.clientX - rect.left) / rect.width
            setCurrentT(Math.max(0, Math.min(1, t)))
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              height: '100%',
              width: `${currentT * 100}%`,
              background: 'var(--accent)',
              borderRadius: 2,
              transition: isPlaying ? 'none' : 'width 0.05s',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: `${currentT * 100}%`,
              transform: 'translate(-50%, -50%)',
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: 'var(--accent)',
              boxShadow: '0 0 6px var(--accent-glow)',
            }}
          />
        </div>
      </div>

      {/* Divider */}
      <div style={{ width: 1, height: 20, background: 'var(--border-subtle)', margin: '0 4px' }} />

      {/* Loop toggle */}
      <button
        className={`btn-icon${loopPlayback ? ' active' : ''}`}
        title={loopPlayback ? 'Loop: On' : 'Loop: Off'}
        onClick={() => setLoopPlayback(!loopPlayback)}
        style={{ fontSize: 13 }}
      >
        🔁
      </button>

      {/* Grid toggle (cosmetic) */}
      <button
        className="btn-icon"
        title="Toggle grid"
        style={{ fontSize: 13 }}
        onClick={() => {}}
      >
        ⊞
      </button>

      {/* Fit to screen (cosmetic) */}
      <button
        className="btn-icon"
        title="Fit to screen"
        style={{ fontSize: 13 }}
        onClick={() => {}}
      >
        ⊡
      </button>

      {/* Divider */}
      <div style={{ width: 1, height: 20, background: 'var(--border-subtle)', margin: '0 4px' }} />

      {/* FPS display */}
      <div
        style={{
          fontFamily: 'JetBrains Mono, Fira Code, monospace',
          fontSize: 10,
          color: 'var(--text-dim)',
          padding: '0 6px',
        }}
      >
        {FPS} FPS
      </div>

      {/* T display */}
      <div
        style={{
          fontFamily: 'JetBrains Mono, Fira Code, monospace',
          fontSize: 10,
          color: 'var(--text-dim)',
          padding: '0 6px',
          minWidth: 40,
          textAlign: 'right',
        }}
      >
        t={currentT.toFixed(3)}
      </div>
    </div>
  )
}
