import React, { useRef, useEffect, useCallback } from 'react'
import useStore from '../store/useStore'

const RULER_H = 24
const TRACK_H = 28
const NAME_W = 160

const TRACK_COLORS = [
  '#00d2ff',
  '#ff50b4',
  '#50ff8c',
  '#ffc832',
  '#b450ff',
  '#ff8c32',
  '#ff5050',
  '#32c8ff',
]

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function roundRect(ctx, x, y, w, h, r) {
  if (w < 2 * r) r = w / 2
  if (h < 2 * r) r = h / 2
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

export default function Timeline() {
  const assets = useStore((s) => s.assets)
  const selectedId = useStore((s) => s.selectedId)
  const currentT = useStore((s) => s.currentT)
  const setCurrentT = useStore((s) => s.setCurrentT)

  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const isDraggingRef = useRef(false)
  const canvasWidthRef = useRef(800)

  // Total timeline duration in seconds
  const totalDuration = Math.max(
    10,
    ...assets.map((a) => a.delay + a.duration + 0.5)
  )

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    const trackAreaW = W - NAME_W

    // Clear
    ctx.clearRect(0, 0, W, H)

    // Background
    ctx.fillStyle = '#111'
    ctx.fillRect(0, 0, W, H)

    // Ruler background
    ctx.fillStyle = '#1a1a1a'
    ctx.fillRect(0, 0, W, RULER_H)

    // Ruler tick marks and labels
    ctx.font = '10px JetBrains Mono, Fira Code, monospace'
    ctx.fillStyle = '#555'

    const pxPerSec = trackAreaW / totalDuration

    // Minor ticks every 0.25s
    for (let t = 0; t <= totalDuration; t += 0.25) {
      const x = NAME_W + t * pxPerSec
      const isMajor = Math.abs(t - Math.round(t)) < 0.01
      ctx.strokeStyle = isMajor ? '#3a3a3a' : '#252525'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, RULER_H - (isMajor ? 10 : 5))
      ctx.lineTo(x, RULER_H)
      ctx.stroke()

      if (isMajor) {
        ctx.fillStyle = '#555'
        const label = `${Math.round(t)}s`
        ctx.fillText(label, x + 3, RULER_H - 12)
      }
    }

    // Draw name column separator line (ruler area)
    ctx.strokeStyle = '#2a2a2a'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(NAME_W, 0)
    ctx.lineTo(NAME_W, H)
    ctx.stroke()

    // Ruler bottom border
    ctx.strokeStyle = '#2a2a2a'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, RULER_H)
    ctx.lineTo(W, RULER_H)
    ctx.stroke()

    // Draw tracks
    assets.forEach((asset, i) => {
      const trackY = RULER_H + i * TRACK_H
      const isSelected = asset.id === selectedId

      // Track background
      ctx.fillStyle = isSelected ? 'rgba(0,210,255,0.05)' : (i % 2 === 0 ? '#131313' : '#111')
      ctx.fillRect(0, trackY, W, TRACK_H)

      // Track bottom border
      ctx.strokeStyle = '#1d1d1d'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, trackY + TRACK_H)
      ctx.lineTo(W, trackY + TRACK_H)
      ctx.stroke()

      // Name column
      ctx.save()
      ctx.rect(0, trackY, NAME_W - 6, TRACK_H)
      ctx.clip()
      ctx.font = isSelected ? '500 11px Inter, system-ui, sans-serif' : '400 11px Inter, system-ui, sans-serif'
      ctx.fillStyle = isSelected ? '#e8e8e8' : '#888'
      ctx.fillText(asset.name, 10, trackY + TRACK_H / 2 + 4)
      ctx.restore()

      // Duration bar
      const barColor = TRACK_COLORS[i % TRACK_COLORS.length]
      const barX = NAME_W + asset.delay * pxPerSec
      const barW = Math.max(4, asset.duration * pxPerSec)
      const barY = trackY + 4
      const barH = TRACK_H - 8

      // Bar fill
      ctx.fillStyle = hexToRgba(barColor, 0.25)
      roundRect(ctx, barX, barY, barW, barH, 3)
      ctx.fill()

      // Bar border
      ctx.strokeStyle = hexToRgba(barColor, 0.7)
      ctx.lineWidth = 1
      roundRect(ctx, barX, barY, barW, barH, 3)
      ctx.stroke()

      // Bar label (if wide enough)
      if (barW > 40) {
        ctx.save()
        ctx.rect(barX + 2, barY, barW - 4, barH)
        ctx.clip()
        ctx.font = '10px JetBrains Mono, monospace'
        ctx.fillStyle = barColor
        ctx.fillText(`${asset.anim} · ${asset.duration}s`, barX + 6, barY + barH / 2 + 3)
        ctx.restore()
      }

      // Delay indicator (if any)
      if (asset.delay > 0) {
        const delayW = asset.delay * pxPerSec
        ctx.fillStyle = 'rgba(255,255,255,0.04)'
        ctx.fillRect(NAME_W, barY, delayW, barH)
        ctx.strokeStyle = 'rgba(255,255,255,0.1)'
        ctx.lineWidth = 1
        ctx.setLineDash([3, 3])
        ctx.beginPath()
        ctx.moveTo(NAME_W, barY)
        ctx.lineTo(NAME_W + delayW, barY + barH)
        ctx.stroke()
        ctx.setLineDash([])
      }
    })

    // Fill remaining track area if no assets
    if (assets.length === 0) {
      ctx.fillStyle = '#131313'
      ctx.fillRect(0, RULER_H, W, H - RULER_H)
      ctx.font = '11px Inter, system-ui, sans-serif'
      ctx.fillStyle = '#2a2a2a'
      ctx.textAlign = 'center'
      ctx.fillText('No layers in timeline', W / 2, RULER_H + (H - RULER_H) / 2 + 4)
      ctx.textAlign = 'left'
    }

    // Playhead line
    const playheadX = NAME_W + currentT * trackAreaW
    ctx.strokeStyle = 'rgba(255,255,255,0.7)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(playheadX, 0)
    ctx.lineTo(playheadX, H)
    ctx.stroke()

    // Playhead triangle (top)
    ctx.fillStyle = '#ffffff'
    ctx.beginPath()
    ctx.moveTo(playheadX - 5, 0)
    ctx.lineTo(playheadX + 5, 0)
    ctx.lineTo(playheadX, 8)
    ctx.closePath()
    ctx.fill()

    // Playhead circle
    ctx.beginPath()
    ctx.arc(playheadX, RULER_H, 4, 0, Math.PI * 2)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
  }, [assets, selectedId, currentT, totalDuration])

  // Resize observer
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width
        canvasWidthRef.current = w
        if (canvasRef.current) {
          canvasRef.current.width = w
          draw()
        }
      }
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [draw])

  // Redraw whenever state changes
  useEffect(() => {
    draw()
  }, [draw])

  const getT = useCallback((clientX) => {
    const canvas = canvasRef.current
    if (!canvas) return 0
    const rect = canvas.getBoundingClientRect()
    const x = clientX - rect.left
    if (x <= NAME_W) return 0
    const trackAreaW = canvas.width - NAME_W
    return Math.max(0, Math.min(1, (x - NAME_W) / trackAreaW))
  }, [])

  const handleMouseDown = useCallback((e) => {
    isDraggingRef.current = true
    setCurrentT(getT(e.clientX))
  }, [getT, setCurrentT])

  const handleMouseMove = useCallback((e) => {
    if (!isDraggingRef.current) return
    setCurrentT(getT(e.clientX))
  }, [getT, setCurrentT])

  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false
  }, [])

  const trackCount = assets.length
  const canvasH = RULER_H + Math.max(1, trackCount) * TRACK_H

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: 180,
        minHeight: 180,
        maxHeight: 180,
        background: '#111',
        borderTop: '1px solid var(--border-default)',
        flexShrink: 0,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Header */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          zIndex: 2,
          padding: '4px 10px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          pointerEvents: 'none',
        }}
      >
        <span className="section-header" style={{ opacity: 0.5 }}>Timeline</span>
      </div>

      {/* Scrollable track area */}
      <div style={{ width: '100%', height: '100%', overflowY: 'auto', overflowX: 'hidden' }}>
        <canvas
          ref={canvasRef}
          width={canvasWidthRef.current}
          height={Math.max(canvasH, 156)}
          style={{ display: 'block', cursor: 'crosshair' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        />
      </div>
    </div>
  )
}
