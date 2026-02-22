# 🎬 MorphStudio – Vector Motion Engine

### _Premium Cinematic Motion Design for Manim_

**MorphStudio** is a high-end visual editor and orchestrator designed to bridge the gap between static SVG assets and dynamic Manim animations. It features a professional **Liquid Glass** aesthetic, emphasizing spatial depth, ambient movement, and mathematical precision.

---

## 💎 Premium Features

### 🎞️ Cinematic Liquid Canvas

- **Liquid Glass Interface**: Translucent, layered panels with simulated backdrop blur and macOS-style 16px corners.
- **Ambient Atmosphere**: A deep blue-black background with slow-moving, multi-layered radial gradients (Indigo, Purple, Cyan).
- **16:9 Pixel Parity**: Strictly locked to Manim's export dimensions ($14.22 \times 8.0$ units) with a uniform $56.25 \text{px/unit}$ scale.
- **Zero-Noise Viewport**: Technical guides and handles vanish in Preview mode, leaving only a pure cinematic monitor.

### 🔄 State-Based Motion Engine

- **Deterministic Transforms**: Define objects via explicit `Initial State` and `Final State`.
- **Interactive Path Handles**: Real-time manipulation of motion arcs and pivot points.
- **Interpolation Accuracy**: Preview complex eases and paths instantly with a high-fidelity timeline.

### 🎭 Smart SVG Morphing

- **Path-to-Path Interpolation**: Seamlessly transform SVG A into SVG B.
- **Code Orchestration**: Generates production-ready Manim code (`ReplacementTransform`, `ReplacementTransform`, etc.).

### 🛠️ Professional Workspace

- **PROPERTIES Panel**: Rebuilt with a clean hierarchy, 24px internal padding, and structured sections (Transform, Motion, Stage).
- **SMART TOOLS**: One-click "Center to Stage" and "Distribute Horizontally" utilities.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [Manim Community Edition](https://docs.manim.community/en/stable/installation.html)
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

- **Framework**: PySide6 (Qt for Python 6.7+)
- **Rendering Core**: Manim Community Edition
- **SVG Logic**: QSvgRenderer with high-precision bounding box calculation
- **UI System**: **Liquid Glass** (Custom CSS layering with backdrop blur simulation)

---

## 📐 Architecture

MorphStudio follows a deterministic data-driven architecture:

1.  **Coordinate Layer**: Maps QGraphicsScene pixels to Manim units with zero-drift precision.
2.  **Atmosphere Layer**: Manages ambient background shaders for a premium creative feel.
3.  **Export Layer**: Generates human-readable, PEP-8 compliant Manim scene code.

---

## 🎨 Design Philosophy

Every element stays on the **8px Grid**. The UI emphasizes spatial hierarchy, "Breathable" 24px padding, and interactive glass depth to ensure a professional production environment.

---

_Created with ❤️ for the Manim Community._
