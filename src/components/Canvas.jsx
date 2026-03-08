import React, { useRef, useEffect, useState, useCallback } from 'react'
import { Stage, Layer, Rect, Image, Line, Circle, Arrow, Group, Text } from 'react-konva'
import useImage from 'use-image'
import useStore from '../store/useStore'

// Canvas constants
const CANVAS_SCALE = 56.25
const STAGE_W = 800
const STAGE_H = 450
const CX = STAGE_W / 2
const CY = STAGE_H / 2

// Coordinate conversions
const mToCx = (x) => CX + x * CANVAS_SCALE
const mToCy = (y) => CY - y * CANVAS_SCALE
const cxToM = (cx) => (cx - CX) / CANVAS_SCALE
const cyToM = (cy) => -(cy - CY) / CANVAS_SCALE

// Easing functions
function easeSmooth(t) { return t * t * (3 - 2 * t) }
function easeLinear(t) { return t }
function easeInExpo(t) { return t === 0 ? 0 : Math.pow(2, 10 * (t - 1)) }
function easeEaseOut(t) { return 1 - (1 - t) * (1 - t) }

function applyEasing(t, easing) {
  if (easing === 'Linear') return easeLinear(t)
  if (easing === 'InExpo') return easeInExpo(t)
  if (easing === 'EaseOut') return easeEaseOut(t)
  return easeSmooth(t)
}

function interpolate(init, fin, t, easing) {
  const et = applyEasing(Math.max(0, Math.min(1, t)), easing)
  const lerp = (a, b) => a + (b - a) * et
  return {
    x: lerp(init.x, fin.x),
    y: lerp(init.y, fin.y),
    scale: lerp(init.scale, fin.scale),
    rotation: lerp(init.rotation, fin.rotation),
    opacity: lerp(init.opacity, fin.opacity),
  }
}

// Individual SVG item inside Konva
function SVGItem({ asset, isSelected, currentT, isPreview, activeSection, onSelect, onDragEnd, onInitHandleDrag }) {
  const [img] = useImage(asset.svgDataUrl)

  if (!asset.visible) return null

  const { initialState: init, finalState: fin } = asset

  // Compute display state
  const displayState = isPreview
    ? interpolate(init, fin, currentT, asset.easing)
    : fin

  const groupX = mToCx(displayState.x)
  const groupY = mToCy(displayState.y)

  // Size the image to 100x100 max preserving aspect
  let imgW = 100
  let imgH = 100
  if (img) {
    const nat = img.naturalWidth || img.width || 100
    const natH = img.naturalHeight || img.height || 100
    const aspect = nat / natH
    if (aspect >= 1) {
      imgW = 100
      imgH = 100 / aspect
    } else {
      imgH = 100
      imgW = 100 * aspect
    }
  }

  const handleDragEnd = useCallback((e) => {
    const node = e.target
    const newFx = cxToM(node.x())
    const newFy = cyToM(node.y())
    const dx = newFx - fin.x
    const dy = newFy - fin.y
    onDragEnd(asset.id, {
      finalState: { x: newFx, y: newFy },
      initialState: { x: init.x + dx, y: init.y + dy },
    })
  }, [asset.id, fin.x, fin.y, init.x, init.y, onDragEnd])

  // Motion path: draw relative to group (which is at fin position)
  const ix = mToCx(init.x) - mToCx(fin.x)
  const iy = mToCy(init.y) - mToCy(fin.y)
  const showMotionPath = isSelected && activeSection === 'MOTION'

  // Ghost frames
  const ghostTs = [0.17, 0.33, 0.5, 0.67, 0.83]

  return (
    <Group
      x={groupX}
      y={groupY}
      rotation={displayState.rotation}
      scaleX={displayState.scale}
      scaleY={displayState.scale}
      opacity={displayState.opacity}
      draggable={!asset.locked}
      onClick={onSelect}
      onTap={onSelect}
      onDragEnd={handleDragEnd}
    >
      {/* Ghost frames for motion path */}
      {showMotionPath && ghostTs.map((gt, gi) => {
        const gs = interpolate(init, fin, gt, asset.easing)
        const gx = mToCx(gs.x) - mToCx(fin.x)
        const gy = mToCy(gs.y) - mToCy(fin.y)
        return (
          <Image
            key={gi}
            image={img}
            x={gx}
            y={gy}
            width={imgW}
            height={imgH}
            offsetX={imgW / 2}
            offsetY={imgH / 2}
            opacity={0.15}
            listening={false}
          />
        )
      })}

      {/* Motion path line and arrow */}
      {showMotionPath && Math.abs(ix) + Math.abs(iy) > 2 && (
        <>
          <Line
            points={[ix, iy, 0, 0]}
            stroke="rgba(0,210,255,0.5)"
            strokeWidth={1}
            dash={[4, 4]}
            listening={false}
          />
          <Arrow
            points={[ix * 0.3 + 0, iy * 0.3 + 0, 0, 0]}
            stroke="rgba(0,210,255,0.7)"
            fill="rgba(0,210,255,0.7)"
            strokeWidth={1}
            pointerLength={8}
            pointerWidth={6}
            listening={false}
          />
          {/* Start handle — draggable circle */}
          <Circle
            x={ix}
            y={iy}
            radius={5}
            fill="#00d2ff"
            stroke="#fff"
            strokeWidth={1}
            draggable
            onDragEnd={(e) => {
              const nx = e.target.x()
              const ny = e.target.y()
              const newInitX = cxToM(mToCx(fin.x) + nx)
              const newInitY = cyToM(mToCy(fin.y) + ny)
              onInitHandleDrag(asset.id, { x: newInitX, y: newInitY })
              // Reset circle position so it stays at correct spot
              e.target.x(ix)
              e.target.y(iy)
            }}
          />
        </>
      )}

      {/* Main SVG image */}
      {img && (
        <Image
          image={img}
          width={imgW}
          height={imgH}
          offsetX={imgW / 2}
          offsetY={imgH / 2}
        />
      )}

      {/* Selection ring */}
      {isSelected && (
        <Rect
          x={-imgW / 2 - 3}
          y={-imgH / 2 - 3}
          width={imgW + 6}
          height={imgH + 6}
          stroke="#00d2ff"
          strokeWidth={1.5}
          dash={[4, 3]}
          fill="transparent"
          listening={false}
        />
      )}
    </Group>
  )
}

// Animated background layer using Konva Rects with gradient fills
function AnimatedBackground({ bgColor, phase }) {
  const rad = (deg) => (deg * Math.PI) / 180

  // Oscillating centers
  const aX = CX + Math.cos(rad(phase)) * 200
  const aY = CY + Math.sin(rad(phase * 0.7)) * 120
  const bX = CX + Math.cos(rad(phase + 180)) * 160
  const bY = CY + Math.sin(rad(phase * 0.5 + 90)) * 100

  return (
    <>
      {/* Base fill */}
      <Rect x={0} y={0} width={STAGE_W} height={STAGE_H} fill={bgColor} listening={false} />

      {/* Layer A: deep indigo radial glow */}
      <Rect
        x={0} y={0} width={STAGE_W} height={STAGE_H}
        fillRadialGradientStartPoint={{ x: aX, y: aY }}
        fillRadialGradientStartRadius={0}
        fillRadialGradientEndPoint={{ x: aX, y: aY }}
        fillRadialGradientEndRadius={380}
        fillRadialGradientColorStops={[0, 'rgba(40,20,80,0.45)', 1, 'rgba(0,0,0,0)']}
        listening={false}
      />

      {/* Layer B: purple glow, opposite side */}
      <Rect
        x={0} y={0} width={STAGE_W} height={STAGE_H}
        fillRadialGradientStartPoint={{ x: bX, y: bY }}
        fillRadialGradientStartRadius={0}
        fillRadialGradientEndPoint={{ x: bX, y: bY }}
        fillRadialGradientEndRadius={300}
        fillRadialGradientColorStops={[0, 'rgba(60,15,80,0.35)', 1, 'rgba(0,0,0,0)']}
        listening={false}
      />

      {/* Layer C: top-left cyan glow */}
      <Rect
        x={0} y={0} width={STAGE_W} height={STAGE_H}
        fillRadialGradientStartPoint={{ x: 80, y: 60 }}
        fillRadialGradientStartRadius={0}
        fillRadialGradientEndPoint={{ x: 80, y: 60 }}
        fillRadialGradientEndRadius={280}
        fillRadialGradientColorStops={[0, 'rgba(0,40,60,0.3)', 1, 'rgba(0,0,0,0)']}
        listening={false}
      />
    </>
  )
}

// Vignette overlay
function Vignette() {
  return (
    <Rect
      x={0} y={0} width={STAGE_W} height={STAGE_H}
      fillRadialGradientStartPoint={{ x: CX, y: CY }}
      fillRadialGradientStartRadius={0}
      fillRadialGradientEndPoint={{ x: CX, y: CY }}
      fillRadialGradientEndRadius={Math.max(STAGE_W, STAGE_H) * 0.72}
      fillRadialGradientColorStops={[0, 'rgba(0,0,0,0)', 0.7, 'rgba(0,0,0,0)', 1, 'rgba(0,0,0,0.55)']}
      listening={false}
    />
  )
}

// Error boundary wrapper
class CanvasErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex-1 flex items-center justify-center"
          style={{ background: '#0a0a0a', color: 'var(--error)', flexDirection: 'column', gap: 8 }}
        >
          <div style={{ fontSize: 14 }}>Canvas Error</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            {this.state.error?.message || 'Unknown error'}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function Canvas() {
  const assets = useStore((s) => s.assets)
  const selectedId = useStore((s) => s.selectedId)
  const currentT = useStore((s) => s.currentT)
  const activeSection = useStore((s) => s.activeSection)
  const bgColor = useStore((s) => s.bgColor)
  const isPlaying = useStore((s) => s.isPlaying)
  const selectAsset = useStore((s) => s.selectAsset)
  const updateAsset = useStore((s) => s.updateAsset)
  const pushUndo = useStore((s) => s.pushUndo)

  const phaseRef = useRef(0)
  const [phase, setPhase] = useState(0)
  const animRef = useRef(null)
  const lastTimeRef = useRef(null)

  // Animate background phase
  useEffect(() => {
    let running = true

    const tick = (ts) => {
      if (!running) return
      if (lastTimeRef.current === null) lastTimeRef.current = ts
      const dt = ts - lastTimeRef.current
      lastTimeRef.current = ts
      // Full cycle in 12 seconds: 360 / 12000 ms = 0.03 deg/ms
      phaseRef.current = (phaseRef.current + dt * 0.03) % 360
      setPhase(phaseRef.current)
      animRef.current = requestAnimationFrame(tick)
    }

    animRef.current = requestAnimationFrame(tick)
    return () => {
      running = false
      if (animRef.current) cancelAnimationFrame(animRef.current)
    }
  }, [])

  const handleStageClick = useCallback((e) => {
    if (e.target === e.target.getStage()) {
      selectAsset(null)
    }
  }, [selectAsset])

  const handleDragEnd = useCallback((id, updates) => {
    pushUndo()
    updateAsset(id, updates)
  }, [pushUndo, updateAsset])

  const handleInitHandleDrag = useCallback((id, newInit) => {
    updateAsset(id, { initialState: newInit })
  }, [updateAsset])

  return (
    <CanvasErrorBoundary>
      <div
        className="flex-1 flex items-center justify-center"
        style={{ background: '#0a0a0a', overflow: 'hidden', position: 'relative' }}
      >
        <div className="stage-glow relative" style={{ lineHeight: 0 }}>
          <Stage
            width={STAGE_W}
            height={STAGE_H}
            onClick={handleStageClick}
            onTap={handleStageClick}
          >
            {/* Background layer */}
            <Layer listening={false}>
              <AnimatedBackground bgColor={bgColor} phase={phase} />
            </Layer>

            {/* SVG items layer */}
            <Layer>
              {assets.map((asset) => (
                <SVGItem
                  key={asset.id}
                  asset={asset}
                  isSelected={asset.id === selectedId}
                  currentT={currentT}
                  isPreview={isPlaying}
                  activeSection={activeSection}
                  onSelect={() => selectAsset(asset.id)}
                  onDragEnd={handleDragEnd}
                  onInitHandleDrag={handleInitHandleDrag}
                />
              ))}
            </Layer>

            {/* Stage border */}
            <Layer listening={false}>
              <Rect
                x={0} y={0}
                width={STAGE_W} height={STAGE_H}
                stroke="rgba(255,255,255,0.06)"
                strokeWidth={1}
                fill="transparent"
                listening={false}
              />
            </Layer>

            {/* Vignette layer */}
            <Layer listening={false}>
              <Vignette />
            </Layer>
          </Stage>
        </div>

        {/* Empty state overlay */}
        {assets.length === 0 && (
          <div
            style={{
              position: 'absolute',
              pointerEvents: 'none',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <div style={{ fontSize: 28, opacity: 0.12 }}>◈</div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', letterSpacing: '0.08em' }}>
              Import SVGs to begin
            </div>
          </div>
        )}
      </div>
    </CanvasErrorBoundary>
  )
}
