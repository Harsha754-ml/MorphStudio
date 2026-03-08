import React, { useEffect, useState, useRef } from 'react'
import useStore from './store/useStore'
import Canvas from './components/Canvas'
import LayerPanel from './components/LayerPanel'
import Inspector from './components/Inspector'
import Timeline from './components/Timeline'
import Transport from './components/Transport'

// ─── MenuButton ─────────────────────────────────────────────────────────────

function MenuButton({ label, items }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const handle = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    window.addEventListener('mousedown', handle)
    return () => window.removeEventListener('mousedown', handle)
  }, [open])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        className="btn"
        style={{
          background: open ? 'var(--bg-raised)' : 'transparent',
          border: '1px solid transparent',
          borderColor: open ? 'var(--border-default)' : 'transparent',
          fontSize: 11,
          padding: '3px 10px',
          color: open ? 'var(--text-primary)' : 'var(--text-secondary)',
        }}
        onClick={() => setOpen((v) => !v)}
      >
        {label}
      </button>

      {open && (
        <div
          className="fade-in"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: 2,
            background: 'var(--bg-overlay)',
            border: '1px solid var(--border-default)',
            borderRadius: 6,
            padding: '4px 0',
            minWidth: 180,
            zIndex: 9999,
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          }}
        >
          {items.map((item, i) =>
            item.separator ? (
              <div key={i} style={{ height: 1, background: 'var(--border-subtle)', margin: '3px 0' }} />
            ) : (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 14px',
                  cursor: 'pointer',
                  color: 'var(--text-primary)',
                  fontSize: 12,
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                }}
                onClick={() => {
                  setOpen(false)
                  item.action?.()
                }}
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span
                    style={{
                      fontSize: 10,
                      color: 'var(--text-dim)',
                      fontFamily: 'monospace',
                      marginLeft: 16,
                    }}
                  >
                    {item.shortcut}
                  </span>
                )}
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}

// ─── ConsolePanel ────────────────────────────────────────────────────────────

function ConsolePanel() {
  const consoleLines = useStore((s) => s.consoleLines)
  const showConsole = useStore((s) => s.showConsole)
  const toggleConsole = useStore((s) => s.toggleConsole)
  const clearConsole = useStore((s) => s.clearConsole)
  const scrollRef = useRef(null)

  // Auto-scroll to bottom on new lines
  useEffect(() => {
    if (scrollRef.current && showConsole) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [consoleLines, showConsole])

  const displayLines = consoleLines.slice(-50)

  return (
    <div
      style={{
        flexShrink: 0,
        background: 'var(--bg-panel)',
        borderTop: '1px solid var(--border-default)',
        display: 'flex',
        flexDirection: 'column',
        height: showConsole ? 120 : 26,
        transition: 'height 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Console header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          height: 26,
          minHeight: 26,
          padding: '0 12px',
          gap: 8,
          borderBottom: showConsole ? '1px solid var(--border-subtle)' : 'none',
          flexShrink: 0,
        }}
      >
        <span className="section-header" style={{ flex: 1 }}>Console</span>

        {consoleLines.length > 0 && (
          <span
            style={{
              fontSize: 9,
              color: 'var(--text-dim)',
              fontFamily: 'monospace',
            }}
          >
            {consoleLines.length} lines
          </span>
        )}

        <button
          className="btn-icon"
          style={{ width: 20, height: 20, fontSize: 10 }}
          onClick={clearConsole}
          title="Clear console"
        >
          ✕
        </button>

        <button
          className="btn-icon"
          style={{ width: 20, height: 20, fontSize: 10 }}
          onClick={toggleConsole}
          title={showConsole ? 'Collapse console' : 'Expand console'}
        >
          {showConsole ? '▾' : '▴'}
        </button>
      </div>

      {/* Console output */}
      {showConsole && (
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '4px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
          }}
        >
          {displayLines.length === 0 ? (
            <div
              style={{
                fontSize: 11,
                color: 'var(--text-dim)',
                fontFamily: 'JetBrains Mono, monospace',
                padding: '4px 0',
              }}
            >
              No output yet. Start a render to see logs.
            </div>
          ) : (
            displayLines.map((line, i) => {
              const isError =
                line.toLowerCase().includes('[error]') ||
                line.toLowerCase().includes('error:') ||
                line.toLowerCase().includes('traceback')
              const isSuccess =
                line.toLowerCase().includes('[done]') ||
                line.toLowerCase().includes('success')
              return (
                <div
                  key={i}
                  className={`console-line${isError ? ' error' : isSuccess ? ' success' : ''}`}
                >
                  {line}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

// ─── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  const undo = useStore((s) => s.undo)
  const redo = useStore((s) => s.redo)
  const saveProject = useStore((s) => s.saveProject)
  const loadProject = useStore((s) => s.loadProject)
  const clearAll = useStore((s) => s.clearAll)

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key === 'z') {
        e.preventDefault()
        undo()
      }
      if (e.ctrlKey && e.key === 'y') {
        e.preventDefault()
        redo()
      }
      if (e.ctrlKey && e.shiftKey && e.key === 'Z') {
        e.preventDefault()
        redo()
      }
      if (e.ctrlKey && e.key === 's' && !e.shiftKey) {
        e.preventDefault()
        // Quick save not wired to dialog here — handled by menu
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [undo, redo])

  const fileMenuItems = [
    {
      label: 'New Project',
      shortcut: 'Ctrl+N',
      action: () => {
        if (window.confirm?.('Start a new project? Unsaved work will be lost.') !== false) {
          clearAll()
        }
      },
    },
    { separator: true },
    {
      label: 'Open Project...',
      shortcut: 'Ctrl+O',
      action: async () => {
        const result = await window.api?.openFile?.([{ name: 'MorphStudio', extensions: ['morphs'] }])
        if (result && !result.canceled && result.filePaths?.[0]) {
          loadProject(result.filePaths[0])
        }
      },
    },
    {
      label: 'Save Project...',
      shortcut: 'Ctrl+S',
      action: async () => {
        const result = await window.api?.saveFile?.([{ name: 'MorphStudio', extensions: ['morphs'] }])
        if (result && !result.canceled && result.filePath) {
          saveProject(result.filePath)
        }
      },
    },
    { separator: true },
    {
      label: 'Exit',
      action: () => {
        window.close?.()
      },
    },
  ]

  const editMenuItems = [
    {
      label: 'Undo',
      shortcut: 'Ctrl+Z',
      action: undo,
    },
    {
      label: 'Redo',
      shortcut: 'Ctrl+Y',
      action: redo,
    },
  ]

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--bg-base)',
      }}
    >
      {/* ── Top Bar ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          height: 40,
          minHeight: 40,
          padding: '0 12px',
          background: 'var(--bg-panel)',
          borderBottom: '1px solid var(--border-default)',
          flexShrink: 0,
          gap: 6,
        }}
      >
        {/* Logo */}
        <span
          style={{
            color: 'var(--accent)',
            fontSize: 18,
            fontWeight: 700,
            lineHeight: 1,
            marginRight: 2,
          }}
        >
          ◈
        </span>
        <span
          style={{
            color: 'var(--text-primary)',
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: '-0.01em',
          }}
        >
          MorphStudio
        </span>
        <span
          style={{
            color: 'var(--text-dim)',
            fontSize: 9,
            marginLeft: 4,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}
        >
          Vector Motion Engine
        </span>

        {/* Divider */}
        <div style={{ width: 1, height: 16, background: 'var(--border-subtle)', margin: '0 6px' }} />

        {/* Menu buttons */}
        <MenuButton label="File" items={fileMenuItems} />
        <MenuButton label="Edit" items={editMenuItems} />

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Version badge */}
        <div
          style={{
            fontSize: 9,
            color: 'var(--text-dim)',
            fontFamily: 'JetBrains Mono, monospace',
            background: 'var(--bg-raised)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 3,
            padding: '2px 6px',
          }}
        >
          v2.0
        </div>
      </div>

      {/* ── Main Work Area ── */}
      <div
        style={{
          display: 'flex',
          flex: 1,
          overflow: 'hidden',
          minHeight: 0,
        }}
      >
        <LayerPanel />
        <Canvas />
        <Inspector />
      </div>

      {/* ── Transport Bar ── */}
      <Transport />

      {/* ── Timeline ── */}
      <Timeline />

      {/* ── Console ── */}
      <ConsolePanel />
    </div>
  )
}
