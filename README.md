# 🎬 SVG Studio Pro

### _The Cinematic Motion Design Environment for Manim_

**SVG Studio Pro** is a high-fidelity visual editor designed to bridge the gap between static SVG assets and dynamic Manim animations. It provides a professional, "Stage-First" workflow for creating complex motion graphics with mathematical precision.

---

## 💎 Premium Features

### 🎞️ Cinematic Canvas

- **16:9 Aspect Ratio Lock**: Perfectly matches Manim's export dimensions (14.22 x 8.0 units).
- **Zero-Noise UI**: Technical guides and handles vanish in Preview mode, leaving only your art.
- **Vignette & Neutral Framing**: Focus on the action with a dimmed stage-surround that mimics professional monitors.

### 🔄 State-Based Motion

- **Deterministic Transforms**: Every object is defined by an explicit `Initial State` and `Final State`.
- **Interactive Path Handles**: Drag the source handle to define where an object comes from, and move the object to define where it ends.
- **Real-time Scrubbing**: Preview complex eases and paths instantly with the precision timeline.

### 🎭 SVG Morph Engine

- **Path-to-Path Interpolation**: Seamlessly transform SVG A into SVG B.
- **Manim Integration**: Exports clean `ReplacementTransform` code for high-quality production renders.

### 🛠️ Contextual Workspace

- **TRANSFORM Mode**: Adjust scale, rotation, and final positions with bounding box feedback.
- **MOTION Mode**: Access motion paths, easing curves, and timing controls.
- **PREVIEW Mode**: A distraction-free cinematic monitor to check your composition.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [Manim](https://docs.manim.community/en/stable/installation.html) (for rendering)
- PySide6

### Installation

```powershell
pip install PySide6
```

### Running the Studio

```powershell
python Studio.py
```

---

## 🛠️ Technology Stack

- **Framework**: PySide6 (Qt for Python)
- **Rendering Core**: Manim (Mathematical Animation Engine)
- **SVG Logic**: QSvgRenderer
- **UI System**: Custom 8px Grid with Glassmorphic design tokens

---

## 📐 Architecture

SVG Studio Pro follows a deterministic data-driven architecture:

1.  **Canvas Layer**: Manages coordinate mapping between QGraphicsScene (Pixels) and Manim (Units).
2.  **Interpolation Layer**: Calculates the state of every object at time `t` based on custom ease functions.
3.  **Export Layer**: Generates clean, human-readable Python code compatible with the latest Manim community versions.

---

## 🎨 Design Philosophy

Every pixel stays on the **8px Grid**. The UI emphasizes spatial hierarchy, high contrast for readability, and interactive micro-animations to ensure a premium user experience.

---

_Created with ❤️ for the Manim Community._
