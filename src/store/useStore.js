import { create } from 'zustand'

function genId() {
  return Math.random().toString(36).slice(2, 10)
}

function cloneAssets(assets) {
  return assets.map((a) => ({
    ...a,
    initialState: { ...a.initialState },
    finalState: { ...a.finalState },
  }))
}

const useStore = create((set, get) => ({
  // State
  assets: [],
  selectedId: null,
  currentT: 0,
  isPlaying: false,
  loopPlayback: true,
  history: [],
  redoStack: [],
  bgColor: '#0a0a0c',
  quality: 'Draft',
  activeSection: 'TRANSFORM',
  consoleLines: [],
  showConsole: true,

  // Actions

  addAsset: (asset) => {
    const state = get()
    const snapshot = cloneAssets(state.assets)
    const history = [...state.history, snapshot].slice(-50)
    set({
      assets: [...state.assets, asset],
      history,
      redoStack: [],
      selectedId: asset.id,
    })
  },

  removeAsset: (id) => {
    const state = get()
    const snapshot = cloneAssets(state.assets)
    const history = [...state.history, snapshot].slice(-50)
    set({
      assets: state.assets.filter((a) => a.id !== id),
      history,
      redoStack: [],
      selectedId: state.selectedId === id ? null : state.selectedId,
    })
  },

  updateAsset: (id, partial) => {
    set((state) => ({
      assets: state.assets.map((a) => {
        if (a.id !== id) return a
        const updated = { ...a, ...partial }
        if (partial.initialState) {
          updated.initialState = { ...a.initialState, ...partial.initialState }
        }
        if (partial.finalState) {
          updated.finalState = { ...a.finalState, ...partial.finalState }
        }
        return updated
      }),
    }))
  },

  selectAsset: (id) => {
    set({ selectedId: id })
  },

  moveAsset: (fromIdx, toIdx) => {
    const state = get()
    const snapshot = cloneAssets(state.assets)
    const history = [...state.history, snapshot].slice(-50)
    const assets = [...state.assets]
    const [moved] = assets.splice(fromIdx, 1)
    assets.splice(toIdx, 0, moved)
    set({ assets, history, redoStack: [] })
  },

  setCurrentT: (t) => {
    set({ currentT: Math.max(0, Math.min(1, t)) })
  },

  setPlaying: (v) => {
    set({ isPlaying: v })
  },

  setLoopPlayback: (v) => {
    set({ loopPlayback: v })
  },

  setBgColor: (v) => {
    set({ bgColor: v })
  },

  setQuality: (v) => {
    set({ quality: v })
  },

  setActiveSection: (v) => {
    set({ activeSection: v })
  },

  pushUndo: () => {
    const state = get()
    const snapshot = cloneAssets(state.assets)
    const history = [...state.history, snapshot].slice(-50)
    set({ history, redoStack: [] })
  },

  undo: () => {
    const state = get()
    if (state.history.length === 0) return
    const history = [...state.history]
    const snapshot = history.pop()
    const redoSnapshot = cloneAssets(state.assets)
    const redoStack = [...state.redoStack, redoSnapshot].slice(-50)
    set({ assets: snapshot, history, redoStack })
  },

  redo: () => {
    const state = get()
    if (state.redoStack.length === 0) return
    const redoStack = [...state.redoStack]
    const snapshot = redoStack.pop()
    const undoSnapshot = cloneAssets(state.assets)
    const history = [...state.history, undoSnapshot].slice(-50)
    set({ assets: snapshot, history, redoStack })
  },

  appendConsole: (line) => {
    set((state) => ({
      consoleLines: [...state.consoleLines, line].slice(-200),
    }))
  },

  clearConsole: () => {
    set({ consoleLines: [] })
  },

  toggleConsole: () => {
    set((state) => ({ showConsole: !state.showConsole }))
  },

  saveProject: async (filePath) => {
    const state = get()
    const data = {
      version: '2.0',
      assets: state.assets,
      bgColor: state.bgColor,
      quality: state.quality,
    }
    const json = JSON.stringify(data, null, 2)
    if (window.api) {
      await window.api.writeFile(filePath, json)
    }
  },

  loadProject: async (filePath) => {
    if (!window.api) return
    const b64 = await window.api.readFile(filePath)
    if (!b64) return
    try {
      const json = atob(b64)
      const data = JSON.parse(json)
      set({
        assets: data.assets || [],
        bgColor: data.bgColor || '#0a0a0c',
        quality: data.quality || 'Draft',
        selectedId: null,
        currentT: 0,
        isPlaying: false,
        history: [],
        redoStack: [],
      })
    } catch (err) {
      console.error('Failed to load project:', err)
    }
  },

  clearAll: () => {
    const state = get()
    const snapshot = cloneAssets(state.assets)
    const history = [...state.history, snapshot].slice(-50)
    set({
      assets: [],
      selectedId: null,
      currentT: 0,
      isPlaying: false,
      history,
      redoStack: [],
    })
  },
}))

export { genId }
export default useStore
