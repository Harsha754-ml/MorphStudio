import React, { useState, useRef } from 'react'
import useStore, { genId } from '../store/useStore'

function basename(filePath) {
  return filePath.replace(/\\/g, '/').split('/').pop() || filePath
}

export default function LayerPanel() {
  const assets = useStore((s) => s.assets)
  const selectedId = useStore((s) => s.selectedId)
  const addAsset = useStore((s) => s.addAsset)
  const removeAsset = useStore((s) => s.removeAsset)
  const updateAsset = useStore((s) => s.updateAsset)
  const selectAsset = useStore((s) => s.selectAsset)
  const moveAsset = useStore((s) => s.moveAsset)
  const clearAll = useStore((s) => s.clearAll)
  const pushUndo = useStore((s) => s.pushUndo)

  const [contextMenu, setContextMenu] = useState(null) // {x, y, assetId}
  const dragFromIdx = useRef(null)
  const [importing, setImporting] = useState(false)

  // Assets displayed in reverse (top of list = front layer = last in array)
  const displayAssets = [...assets].reverse()

  const handleImport = async () => {
    if (importing) return
    setImporting(true)
    try {
      const api = window.api
      if (!api) {
        // Dev fallback: create a demo asset
        const demoId = genId()
        addAsset({
          id: demoId,
          name: 'demo.svg',
          path: '',
          svgDataUrl: `data:image/svg+xml;base64,${btoa('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" fill="#00d2ff" opacity="0.8"/></svg>')}`,
          initialState: { x: -2, y: 0, scale: 1, rotation: 0, opacity: 1 },
          finalState: { x: 2, y: 0, scale: 1, rotation: 0, opacity: 1 },
          anim: 'Path',
          easing: 'Smooth',
          delay: 0,
          duration: 2.0,
          sequenceMode: false,
          visible: true,
          locked: false,
        })
        return
      }

      const result = await api.openFile([{ name: 'SVG Files', extensions: ['svg'] }])
      if (!result || result.canceled || !result.filePaths?.length) return

      const filePath = result.filePaths[0]
      const b64 = await api.readFile(filePath)
      if (!b64) return

      const svgDataUrl = `data:image/svg+xml;base64,${b64}`
      const name = basename(filePath)
      const id = genId()

      addAsset({
        id,
        name,
        path: filePath,
        svgDataUrl,
        initialState: { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 },
        finalState: { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 },
        anim: 'Path',
        easing: 'Smooth',
        delay: 0,
        duration: 2.0,
        sequenceMode: false,
        visible: true,
        locked: false,
      })
    } catch (err) {
      console.error('Import failed:', err)
    } finally {
      setImporting(false)
    }
  }

  const handleDragStart = (e, displayIdx) => {
    // displayIdx is in reversed array, so real index = assets.length - 1 - displayIdx
    dragFromIdx.current = assets.length - 1 - displayIdx
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e, displayIdx) => {
    e.preventDefault()
    if (dragFromIdx.current === null) return
    const toRealIdx = assets.length - 1 - displayIdx
    if (dragFromIdx.current !== toRealIdx) {
      moveAsset(dragFromIdx.current, toRealIdx)
    }
    dragFromIdx.current = null
  }

  const handleContextMenu = (e, assetId) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, assetId })
  }

  const closeContextMenu = () => setContextMenu(null)

  const handleDuplicate = (assetId) => {
    const asset = assets.find((a) => a.id === assetId)
    if (!asset) return
    pushUndo()
    addAsset({
      ...asset,
      id: genId(),
      name: asset.name.replace(/\.svg$/i, '') + '_copy.svg',
      initialState: { ...asset.initialState },
      finalState: { ...asset.finalState },
    })
    closeContextMenu()
  }

  const handleDelete = (assetId) => {
    pushUndo()
    removeAsset(assetId)
    closeContextMenu()
  }

  const handleCenter = (assetId) => {
    pushUndo()
    updateAsset(assetId, {
      initialState: { x: 0, y: 0 },
      finalState: { x: 0, y: 0 },
    })
    closeContextMenu()
  }

  return (
    <div
      style={{
        width: 260,
        minWidth: 260,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-panel)',
        borderRight: '1px solid var(--border-default)',
        overflow: 'hidden',
      }}
      onClick={contextMenu ? closeContextMenu : undefined}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 12px',
          borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}
      >
        <span className="section-header">Layers</span>
        <button
          className="btn btn-accent"
          onClick={handleImport}
          disabled={importing}
          style={{ fontSize: 11, padding: '3px 10px' }}
        >
          {importing ? '...' : '+ Import'}
        </button>
      </div>

      {/* Layer count */}
      <div
        style={{
          padding: '4px 12px',
          fontSize: 10,
          color: 'var(--text-dim)',
          borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}
      >
        {assets.length} {assets.length === 1 ? 'layer' : 'layers'}
      </div>

      {/* Layer list */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {displayAssets.length === 0 && (
          <div
            style={{
              padding: '24px 16px',
              textAlign: 'center',
              color: 'var(--text-dim)',
              fontSize: 11,
              lineHeight: 1.6,
            }}
          >
            No layers yet.
            <br />
            Click <strong style={{ color: 'var(--text-secondary)' }}>+ Import</strong> to add SVGs.
          </div>
        )}

        {displayAssets.map((asset, displayIdx) => {
          const isSelected = asset.id === selectedId
          return (
            <div
              key={asset.id}
              className={`layer-item${isSelected ? ' selected' : ''}`}
              draggable
              onDragStart={(e) => handleDragStart(e, displayIdx)}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, displayIdx)}
              onClick={() => selectAsset(asset.id)}
              onContextMenu={(e) => handleContextMenu(e, asset.id)}
            >
              {/* Drag handle */}
              <span
                style={{
                  color: 'var(--text-dim)',
                  fontSize: 14,
                  cursor: 'grab',
                  lineHeight: 1,
                  flexShrink: 0,
                }}
                title="Drag to reorder"
              >
                ⋮
              </span>

              {/* SVG thumbnail */}
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 4,
                  background: 'var(--bg-raised)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  overflow: 'hidden',
                  opacity: asset.visible ? 1 : 0.35,
                }}
              >
                <img
                  src={asset.svgDataUrl}
                  alt={asset.name}
                  style={{ width: 28, height: 28, objectFit: 'contain' }}
                  draggable={false}
                />
              </div>

              {/* Name */}
              <div
                style={{
                  flex: 1,
                  overflow: 'hidden',
                  minWidth: 0,
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: isSelected ? 500 : 400,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={asset.name}
                >
                  {asset.name}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 1 }}>
                  {asset.anim} · {asset.easing}
                </div>
              </div>

              {/* Eye button */}
              <button
                className="btn-icon"
                style={{
                  flexShrink: 0,
                  fontSize: 13,
                  opacity: asset.visible ? 0.7 : 0.25,
                }}
                onClick={(e) => {
                  e.stopPropagation()
                  updateAsset(asset.id, { visible: !asset.visible })
                }}
                title={asset.visible ? 'Hide layer' : 'Show layer'}
              >
                {asset.visible ? '👁' : '🚫'}
              </button>

              {/* Lock button */}
              <button
                className="btn-icon"
                style={{
                  flexShrink: 0,
                  fontSize: 13,
                  opacity: asset.locked ? 1 : 0.3,
                }}
                onClick={(e) => {
                  e.stopPropagation()
                  updateAsset(asset.id, { locked: !asset.locked })
                }}
                title={asset.locked ? 'Unlock layer' : 'Lock layer'}
              >
                {asset.locked ? '🔒' : '🔓'}
              </button>
            </div>
          )
        })}
      </div>

      {/* Bottom actions */}
      <div
        style={{
          padding: '8px 12px',
          borderTop: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}
      >
        <button
          className="btn btn-danger"
          style={{ width: '100%', textAlign: 'center' }}
          onClick={() => {
            if (assets.length === 0) return
            if (window.confirm?.('Clear all layers?') !== false) {
              clearAll()
            }
          }}
        >
          CLEAR ALL
        </button>
      </div>

      {/* Context menu */}
      {contextMenu && (
        <div
          style={{
            position: 'fixed',
            left: contextMenu.x,
            top: contextMenu.y,
            background: 'var(--bg-overlay)',
            border: '1px solid var(--border-default)',
            borderRadius: 6,
            padding: '4px 0',
            zIndex: 1000,
            minWidth: 140,
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          }}
          className="fade-in"
          onClick={(e) => e.stopPropagation()}
        >
          {[
            { label: 'Duplicate', action: () => handleDuplicate(contextMenu.assetId) },
            { label: 'Center on Stage', action: () => handleCenter(contextMenu.assetId) },
            { label: '──', disabled: true },
            { label: 'Delete', action: () => handleDelete(contextMenu.assetId), danger: true },
          ].map((item, i) =>
            item.label === '──' ? (
              <div key={i} style={{ height: 1, background: 'var(--border-subtle)', margin: '3px 0' }} />
            ) : (
              <div
                key={i}
                onClick={item.disabled ? undefined : item.action}
                style={{
                  padding: '6px 14px',
                  fontSize: 12,
                  cursor: item.disabled ? 'default' : 'pointer',
                  color: item.danger ? 'var(--error)' : 'var(--text-primary)',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => {
                  if (!item.disabled) e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                }}
              >
                {item.label}
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}
