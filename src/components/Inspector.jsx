import React, { useState, useCallback } from 'react'
import useStore from '../store/useStore'

// Collapsible section component
function CollapsibleSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          cursor: 'pointer',
          userSelect: 'none',
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="section-header">{title}</span>
        <span
          style={{
            fontSize: 10,
            color: 'var(--text-dim)',
            transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
            display: 'inline-block',
          }}
        >
          ▶
        </span>
      </div>
      {open && (
        <div className="section-content" style={{ padding: '4px 12px 12px' }}>
          {children}
        </div>
      )}
    </div>
  )
}

// Slider row with label and value display
function SliderRow({ label, value, min, max, step = 1, unit = '', onChange }) {
  return (
    <div className="inspector-row" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="label">{label}</span>
        <span
          className="mono"
          style={{ fontSize: 11, color: 'var(--text-primary)', minWidth: 40, textAlign: 'right' }}
        >
          {typeof value === 'number' ? value.toFixed(step < 1 ? 2 : 0) : value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        className="slider-input"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  )
}

// XY row for position
function XYRow({ labelX, labelY, valueX, valueY, onChangeX, onChangeY }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
      <div>
        <div className="label" style={{ marginBottom: 3 }}>{labelX}</div>
        <input
          type="number"
          className="number-input"
          style={{ width: '100%' }}
          value={valueX}
          step={0.01}
          onChange={(e) => onChangeX(parseFloat(e.target.value) || 0)}
        />
      </div>
      <div>
        <div className="label" style={{ marginBottom: 3 }}>{labelY}</div>
        <input
          type="number"
          className="number-input"
          style={{ width: '100%' }}
          value={valueY}
          step={0.01}
          onChange={(e) => onChangeY(parseFloat(e.target.value) || 0)}
        />
      </div>
    </div>
  )
}

const BG_SWATCHES = [
  { color: '#0a0a0c', label: 'Dark' },
  { color: '#000000', label: 'Black' },
  { color: '#1e1e2e', label: 'Midnight' },
  { color: '#ffffff', label: 'White' },
]

const ANIM_OPTIONS = ['Path', 'Morph', 'FlyIn', 'PopIn', 'Fade', 'Draw']
const EASING_OPTIONS = ['Smooth', 'Linear', 'InExpo', 'InBounce', 'Elastic', 'EaseOut', 'EaseInOut']
const QUALITY_OPTIONS = ['Draft', 'HD', 'Full HD', '4K']

export default function Inspector() {
  const assets = useStore((s) => s.assets)
  const selectedId = useStore((s) => s.selectedId)
  const updateAsset = useStore((s) => s.updateAsset)
  const pushUndo = useStore((s) => s.pushUndo)
  const bgColor = useStore((s) => s.bgColor)
  const quality = useStore((s) => s.quality)
  const setBgColor = useStore((s) => s.setBgColor)
  const setQuality = useStore((s) => s.setQuality)
  const appendConsole = useStore((s) => s.appendConsole)

  const asset = assets.find((a) => a.id === selectedId) || null

  const update = useCallback(
    (partial) => {
      if (!asset) return
      updateAsset(asset.id, partial)
    },
    [asset, updateAsset]
  )

  const updateFinalState = useCallback(
    (partial) => {
      if (!asset) return
      update({ finalState: partial })
    },
    [asset, update]
  )

  // When X position changes: shift initialState by same delta so motion vector is preserved
  const handleXChange = (newX) => {
    if (!asset) return
    const dx = newX - asset.finalState.x
    pushUndo()
    updateAsset(asset.id, {
      finalState: { x: newX },
      initialState: { x: asset.initialState.x + dx },
    })
  }

  const handleYChange = (newY) => {
    if (!asset) return
    const dy = newY - asset.finalState.y
    pushUndo()
    updateAsset(asset.id, {
      finalState: { y: newY },
      initialState: { y: asset.initialState.y + dy },
    })
  }

  const handleDistribute = () => {
    if (assets.length < 2) return
    pushUndo()
    const totalW = 10 // Manim units total spread
    const step = totalW / (assets.length - 1)
    assets.forEach((a, i) => {
      const newX = -totalW / 2 + i * step
      const dx = newX - a.finalState.x
      updateAsset(a.id, {
        finalState: { x: newX },
        initialState: { x: a.initialState.x + dx },
      })
    })
  }

  const handleCenter = () => {
    if (!asset) return
    pushUndo()
    updateAsset(asset.id, {
      finalState: { x: 0, y: 0 },
      initialState: { x: 0, y: 0 },
    })
  }

  const handleRender = async () => {
    appendConsole('Starting render...')
    if (!window.api) {
      appendConsole('[error] window.api not available (not in Electron)')
      return
    }
    window.api.removeRenderListeners()
    window.api.onRenderLog((line) => appendConsole(line))
    window.api.onRenderDone((success) => {
      appendConsole(success ? '[done] Render complete.' : '[error] Render failed.')
    })

    const params = {
      quality,
      global_params: { bg_color: bgColor },
      assets: assets.map((a) => ({
        name: a.name,
        path: a.path,
        initial_state: a.initialState,
        final_state: a.finalState,
        anim: a.anim,
        easing: a.easing,
        delay: a.delay,
        duration: a.duration,
        sequence_mode: a.sequenceMode,
      })),
    }
    await window.api.startRender(params)
  }

  return (
    <div
      style={{
        width: 300,
        minWidth: 300,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-panel)',
        borderLeft: '1px solid var(--border-default)',
        overflow: 'hidden',
      }}
    >
      {/* Panel header */}
      <div
        style={{
          padding: '10px 12px',
          borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}
      >
        <span className="section-header">Properties</span>
        {asset && (
          <span
            style={{
              marginLeft: 8,
              fontSize: 10,
              color: 'var(--text-dim)',
              fontFamily: 'monospace',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: 180,
              display: 'inline-block',
              verticalAlign: 'middle',
            }}
            title={asset.name}
          >
            {asset.name}
          </span>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {!asset ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'var(--text-dim)',
              fontSize: 11,
              textAlign: 'center',
              padding: 24,
            }}
          >
            Select a layer to edit properties
          </div>
        ) : (
          <>
            {/* TRANSFORM SECTION */}
            <CollapsibleSection title="Transform" defaultOpen={true}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Position */}
                <div>
                  <div className="label" style={{ marginBottom: 6 }}>Position (Manim units)</div>
                  <XYRow
                    labelX="X"
                    labelY="Y"
                    valueX={asset.finalState.x.toFixed(2)}
                    valueY={asset.finalState.y.toFixed(2)}
                    onChangeX={handleXChange}
                    onChangeY={handleYChange}
                  />
                </div>

                {/* Scale */}
                <SliderRow
                  label="Scale"
                  value={Math.round(asset.finalState.scale * 100)}
                  min={10}
                  max={500}
                  step={1}
                  unit="%"
                  onChange={(v) => {
                    updateFinalState({ scale: v / 100 })
                  }}
                />

                {/* Rotation */}
                <SliderRow
                  label="Rotation"
                  value={Math.round(asset.finalState.rotation)}
                  min={-360}
                  max={360}
                  step={1}
                  unit="°"
                  onChange={(v) => {
                    updateFinalState({ rotation: v })
                  }}
                />

                {/* Opacity */}
                <SliderRow
                  label="Opacity"
                  value={Math.round(asset.finalState.opacity * 100)}
                  min={0}
                  max={100}
                  step={1}
                  unit="%"
                  onChange={(v) => {
                    updateFinalState({ opacity: v / 100 })
                  }}
                />

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                  <button className="btn" style={{ flex: 1 }} onClick={handleCenter}>
                    CENTER
                  </button>
                  <button className="btn" style={{ flex: 1 }} onClick={handleDistribute}>
                    DISTRIBUTE
                  </button>
                </div>
              </div>
            </CollapsibleSection>

            {/* MOTION SECTION */}
            <CollapsibleSection title="Motion" defaultOpen={true}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Animation type */}
                <div>
                  <div className="label" style={{ marginBottom: 4 }}>Animation</div>
                  <select
                    className="select-input"
                    value={asset.anim}
                    onChange={(e) => {
                      pushUndo()
                      update({ anim: e.target.value })
                    }}
                  >
                    {ANIM_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Easing */}
                <div>
                  <div className="label" style={{ marginBottom: 4 }}>Easing</div>
                  <select
                    className="select-input"
                    value={asset.easing}
                    onChange={(e) => {
                      update({ easing: e.target.value })
                    }}
                  >
                    {EASING_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Delay */}
                <SliderRow
                  label="Delay"
                  value={asset.delay}
                  min={0}
                  max={10}
                  step={0.1}
                  unit="s"
                  onChange={(v) => {
                    update({ delay: v })
                  }}
                />

                {/* Duration */}
                <SliderRow
                  label="Duration"
                  value={asset.duration}
                  min={0.5}
                  max={10}
                  step={0.1}
                  unit="s"
                  onChange={(v) => {
                    update({ duration: v })
                  }}
                />

                {/* After Previous */}
                <label
                  className="inspector-row"
                  style={{ cursor: 'pointer', gap: 8 }}
                  onClick={() => update({ sequenceMode: !asset.sequenceMode })}
                >
                  <div
                    style={{
                      width: 14,
                      height: 14,
                      borderRadius: 3,
                      border: `1px solid ${asset.sequenceMode ? 'var(--accent)' : 'var(--border-default)'}`,
                      background: asset.sequenceMode ? 'var(--accent)' : 'transparent',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      transition: 'background 0.15s, border-color 0.15s',
                    }}
                  >
                    {asset.sequenceMode && (
                      <span style={{ color: '#000', fontSize: 9, fontWeight: 700, lineHeight: 1 }}>✓</span>
                    )}
                  </div>
                  <span className="label">After Previous</span>
                </label>

                {/* Morph target (only for Morph anim) */}
                {asset.anim === 'Morph' && (
                  <button className="btn" style={{ width: '100%' }} onClick={() => {}}>
                    Select Target SVG
                  </button>
                )}

                {/* Initial state section */}
                <div
                  style={{
                    background: 'var(--bg-raised)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 6,
                    padding: '8px 10px',
                  }}
                >
                  <div className="label" style={{ marginBottom: 6, color: 'var(--text-dim)' }}>
                    Initial Position
                  </div>
                  <XYRow
                    labelX="X₀"
                    labelY="Y₀"
                    valueX={asset.initialState.x.toFixed(2)}
                    valueY={asset.initialState.y.toFixed(2)}
                    onChangeX={(v) => {
                      update({ initialState: { x: v } })
                    }}
                    onChangeY={(v) => {
                      update({ initialState: { y: v } })
                    }}
                  />
                </div>
              </div>
            </CollapsibleSection>

            {/* STAGE SECTION */}
            <CollapsibleSection title="Stage" defaultOpen={false}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Background color */}
                <div>
                  <div className="label" style={{ marginBottom: 6 }}>Background</div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {BG_SWATCHES.map((swatch) => (
                      <div
                        key={swatch.color}
                        className={`color-swatch${bgColor === swatch.color ? ' active' : ''}`}
                        style={{ background: swatch.color }}
                        title={swatch.label}
                        onClick={() => setBgColor(swatch.color)}
                      />
                    ))}
                    {/* Custom color input */}
                    <input
                      type="color"
                      value={bgColor}
                      onChange={(e) => setBgColor(e.target.value)}
                      style={{
                        width: 24,
                        height: 24,
                        borderRadius: 4,
                        border: '2px solid var(--border-default)',
                        background: 'transparent',
                        cursor: 'pointer',
                        padding: 0,
                      }}
                      title="Custom color"
                    />
                  </div>
                </div>

                {/* Export quality */}
                <div>
                  <div className="label" style={{ marginBottom: 6 }}>Export Quality</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                    {QUALITY_OPTIONS.map((q) => (
                      <button
                        key={q}
                        className="btn"
                        style={{
                          background: quality === q ? 'var(--accent-dim)' : 'var(--bg-raised)',
                          borderColor: quality === q ? 'var(--accent)' : 'var(--border-subtle)',
                          color: quality === q ? 'var(--accent)' : 'var(--text-secondary)',
                          fontSize: 10,
                          padding: '5px 4px',
                          textAlign: 'center',
                        }}
                        onClick={() => setQuality(q)}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </CollapsibleSection>
          </>
        )}

        {/* RENDER button (always visible) */}
        <div style={{ padding: '12px' }}>
          <button
            className="btn btn-accent"
            style={{
              width: '100%',
              height: 48,
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.08em',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
            onClick={handleRender}
            disabled={assets.length === 0}
          >
            <span>▶</span>
            <span>RENDER EXPORT</span>
          </button>
          <div
            style={{
              marginTop: 6,
              fontSize: 10,
              color: 'var(--text-dim)',
              textAlign: 'center',
            }}
          >
            {quality} quality · {assets.length} layer{assets.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>
    </div>
  )
}
