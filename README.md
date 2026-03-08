<div align="center">

<br/>

```
◈  MorphStudio
```

### **Professional SVG Motion Design Editor**

*The After Effects experience — built for SVG animators*

<br/>

![Version](https://img.shields.io/badge/version-3.0.0-00d2ff?style=flat-square&labelColor=0d0d0d)
![Electron](https://img.shields.io/badge/Electron-31-47848F?style=flat-square&logo=electron&logoColor=white&labelColor=0d0d0d)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=white&labelColor=0d0d0d)
![Konva](https://img.shields.io/badge/Konva.js-9-FF6B35?style=flat-square&labelColor=0d0d0d)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=0d0d0d)
![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square&labelColor=0d0d0d)

<br/>

</div>

---

## What is MorphStudio?

MorphStudio is a **desktop SVG animation editor** that lets you import SVGs, define motion paths, set easing curves, and export cinematic animations via [Manim](https://docs.manim.community/). Think of it as Premiere Pro or After Effects — but purpose-built for SVG motion graphics.

Built with **Electron + React + Konva.js**, it delivers a hardware-accelerated canvas, a real multi-track timeline, and a professional dark UI that gets out of your way.

---

## Features

### Canvas
- **Hardware-accelerated canvas** via Konva.js — smooth 60fps drag and transform
- **Drag SVGs** directly onto the stage with pixel-perfect Manim coordinate sync
- **Motion path overlay** — dashed line + arrowhead showing initial → final trajectory
- **Ghost frames** — 5 semi-transparent previews of the animation at keyframe intervals
- **Start handle** — drag the origin point independently from the destination
- **Animated deep-space background** — three-layer oscillating radial gradients
- **Vignette overlay** — cinematic stage framing

### Timeline
- **Multi-track timeline** — one colored bar per layer showing delay + duration
- **Time ruler** — major (1s) and minor (0.25s) tick marks with time labels
- **Click or drag to scrub** — preview your animation at any point in time
- **Playhead** — white line + triangle that follows playback

### Playback
- **▶ Play / ❚❚ Pause / ⏮ Rewind** transport controls
- **RAF-based playback loop** at 30fps — smooth, non-blocking
- **Loop toggle** — hold after the last frame or bounce back to start
- **Live time display** in seconds

### Layer System
- **Layer panel** with SVG thumbnails, names, and drag-to-reorder
- **Visibility toggle** (👁) — hide layers from canvas without deleting
- **Lock toggle** (🔒) — freeze a layer against accidental moves
- **Right-click context menu** — Duplicate, Delete, Center on Stage

### Inspector

| Section | Controls |
|---|---|
| **TRANSFORM** | X / Y position inputs, Scale, Rotation, Opacity |
| **MOTION** | Animation type, Easing curve, Delay, Duration, Sequence mode |
| **STAGE** | Background color swatches, Export quality, Render button |

### Project
- **Save / Load** `.morphs` project files (JSON)
- **Undo / Redo** — 50-step history with `Ctrl+Z` / `Ctrl+Y`
- **File menu** — New, Open, Save with keyboard shortcuts

### Export
- **Manim-powered render** — exports cinematic MP4 via Python subprocess
- **Quality options** — Draft → HD → Full HD → 4K
- **Live render log** — streamed line-by-line to the console panel

### Animation Types

| Type | Description |
|---|---|
| `Path` | Translate + scale + rotate from initial → final state |
| `Morph` | ReplacementTransform between two SVGs |
| `Fade` | FadeIn from a position |
| `Draw` | Stroke-draw the SVG, then move to final position |
| `FlyIn` | Fly in from the initial position with easing |
| `PopIn` | Scale up from zero with bounce easing |

---

## Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| Python | ≥ 3.9 |
| Manim Community | [Install guide](https://docs.manim.community/en/stable/installation.html) |

### Install & Run

```bash
# Clone
git clone https://github.com/Harsha754-ml/MorphStudio.git
cd MorphStudio

# Install JS dependencies
npm install

# Start the app (Vite dev server + Electron)
npm run dev
```

> **First run?** Electron opens automatically once Vite is ready on port 5173.

---

## Usage

```
1.  Click "IMPORT SVG" or drag an SVG file onto the canvas
2.  Drag the item to set its Final Position
3.  Drag the cyan ◉ start handle to set the Initial Position
4.  Open MOTION panel → choose animation type and easing curve
5.  Set delay and duration
6.  Press ▶ to preview, or drag the timeline playhead to scrub
7.  Open STAGE panel → choose quality → click RENDER STUDIO EXPORT
8.  Find your MP4 in the renders/ directory
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+S` | Save Project |
| `Ctrl+O` | Open Project |
| `Ctrl+N` | New Project |
| `Ctrl+D` | Duplicate selected layer |
| `Delete` / `Backspace` | Delete selected layer |

---

## Project Structure

```
MorphStudio/
├── electron/
│   ├── main.js              ← Electron main process (window, IPC, Python bridge)
│   └── preload.js           ← Context bridge — exposes window.api to renderer
│
├── src/
│   ├── App.jsx              ← Root layout + file menu + console panel
│   ├── index.css            ← Design system (CSS vars, dark theme, components)
│   ├── main.jsx             ← React entry point
│   │
│   ├── store/
│   │   └── useStore.js      ← Zustand state (assets, undo/redo, playback)
│   │
│   └── components/
│       ├── Canvas.jsx       ← Konva stage, SVG items, drag, motion paths
│       ├── LayerPanel.jsx   ← Left sidebar — layers, thumbnails, reorder
│       ├── Inspector.jsx    ← Right panel — TRANSFORM / MOTION / STAGE
│       ├── Timeline.jsx     ← Multi-track timeline (HTML canvas)
│       └── Transport.jsx    ← Playback controls + time display
│
├── studio_core.py           ← Manim scene code generator + render subprocess
├── studio_core_runner.py    ← CLI bridge called by Electron IPC
└── Studio.py                ← Legacy PySide6 version (preserved)
```

---

## Architecture

```
┌─ Renderer Process (React) ──────────────────────────────────┐
│                                                              │
│  App.jsx ─┬─ Canvas.jsx   (Konva — 800×450 stage)           │
│           ├─ LayerPanel.jsx                                  │
│           ├─ Inspector.jsx                                   │
│           ├─ Timeline.jsx  (HTML canvas)                     │
│           └─ Transport.jsx                                   │
│                                                              │
│  useStore.js  (Zustand — asset state, history, playback)    │
│                                                              │
│  window.api  ←── preload.js (IPC bridge, context isolated)  │
└──────────────────────────────────────────────────────────────┘
         │  ipcRenderer.invoke / ipcMain.handle
┌─ Main Process (Electron) ───────────────────────────────────┐
│  dialog.showOpenDialog / showSaveDialog                      │
│  fs.readFileSync / writeFileSync                             │
│  child_process.spawn → python studio_core_runner.py         │
│    └─ studio_core.py → Manim subprocess → renders/          │
└──────────────────────────────────────────────────────────────┘
```

### Coordinate System

MorphStudio uses Manim's coordinate system internally:

```
Canvas center  =  Manim (0, 0)
Stage size     =  14.22 × 8.0 Manim units
Scale factor   =  56.25 px / unit   (800px ÷ 14.22 units)
Y-axis         =  inverted  →  manimY = −(canvasY − 225) / 56.25
```

---

## Roadmap

- [ ] Multi-keyframe animation (N keyframes per property)
- [ ] Bezier path editing directly on canvas
- [ ] Per-property graph editor (velocity curves)
- [ ] SVG element inspector (edit individual paths / fill colors)
- [ ] Lottie JSON export
- [ ] GIF export via canvas frame capture
- [ ] Audio waveform + beat sync
- [ ] Pre-composition (nested scenes)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | [Electron 31](https://electronjs.org) |
| Build tool | [Vite 5](https://vitejs.dev) |
| UI framework | [React 18](https://react.dev) |
| Canvas | [Konva.js 9](https://konvajs.org) + [react-konva](https://github.com/konvajs/react-konva) |
| State | [Zustand 4](https://zustand-demo.pmnd.rs) |
| Styling | [Tailwind CSS 3](https://tailwindcss.com) + CSS variables |
| Render engine | [Manim Community](https://docs.manim.community) (Python) |

---

## License

MIT © [Harsha754-ml](https://github.com/Harsha754-ml)

---

<div align="center">
<sub>Built with obsession. Designed for creators.</sub>
</div>
