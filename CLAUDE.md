# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: MorphStudio

A professional vector motion design editor that bridges static SVG assets with Manim-based cinematic animations. Built with PySide6 (Qt for Python).

## Running the App

```bash
python Studio.py
```

No build step, no test suite, no linter configured. Dependencies must be installed manually:

```bash
pip install PySide6
# Also requires Manim Community Edition: https://docs.manim.community/en/stable/installation.html
```

## Architecture

The app is split into two files:

- **`Studio.py`** (~1,450 lines) — All UI: main window, canvas, inspector panels, layer list, toolbar, and all Qt widgets.
- **`studio_core.py`** (~151 lines) — Rendering engine: generates Manim Python scene code from asset data, then spawns a subprocess to run `manim`.

### Data Flow

1. User imports SVGs → stored as `asset` dicts in `self.assets[]` on `SVGStudioWYSIWYG`
2. User edits transform/motion properties in the right inspector → updates `asset["initial_state"]` / `asset["final_state"]`
3. On render: `StudioCore.generate_scene_code(assets, params)` → writes `_studio_temp.py` → runs `manim` subprocess → output streams to console tab → file cleaned up

### Asset Data Structure

Each asset dict has this shape:

```python
{
    "name": "shape.svg",
    "path": "/abs/path/to/shape.svg",
    "initial_state": { "x": 0.0, "y": 0.0, "scale": 1.0, "rotation": 0, "opacity": 1.0, "svg": "" },
    "final_state":   { "x": 0.0, "y": 0.0, "scale": 1.0, "rotation": 0, "opacity": 1.0, "svg": "" },
    "anim": "Path",       # Path | Morph | Fade | Draw | FlyIn | PopIn
    "easing": "Smooth",   # Smooth | Linear | InExpo | InBounce | Elastic | ...
    "delay": 0.0,
    "duration": 2.0,
    "sequence_mode": False
}
```

### Coordinate System

Critical: the canvas uses a **dual coordinate system**.

- **Manim units**: scene center = `(0, 0)`, Y-axis positive = up. Viewport is `14.22 × 8.0` units.
- **Qt pixels**: `CANVAS_SCALE = 56.25 px/unit`. Y-axis is **inverted** relative to Manim.

Conversion (Manim → Qt scene position):
```python
px = value_x * CANVAS_SCALE
py = -value_y * CANVAS_SCALE   # Note the negation
```

All properties stored in `asset` dicts use **Manim units**. Pixel math only happens inside canvas rendering methods.

### Key Classes

| Class | File | Role |
|---|---|---|
| `SVGStudioWYSIWYG` | Studio.py | Main window; owns `self.assets`, inspector state, and all signal wiring |
| `StudioCanvas` | Studio.py | `QGraphicsView`; handles drag, selection, timeline preview, animated background |
| `DraggableSVGItem` | Studio.py | `QGraphicsItem` for each SVG; renders motion path, ghost frames |
| `StudioCore` | studio_core.py | Stateless rendering helper; pure functions for code gen and subprocess execution |
| `CollapsibleSection` | Studio.py | Reusable expandable panel used throughout the right inspector |

### UI Layout

Three-panel layout: **Left Sidebar** (280px, layers) | **Center Canvas** (flexible) | **Right Inspector** (320px, properties).

Inspector has three collapsible sections: TRANSFORM, MOTION, STAGE.

## Design Conventions

- **8px grid** for all spacing; **24px** internal padding inside panels.
- **Liquid Glass** aesthetic: translucent panels (`rgba` backgrounds), simulated backdrop blur via layered gradients.
- Fonts: `Inter` for UI, `JetBrains Mono` for code/console output.
- All color constants are defined at the top of `Studio.py` (prefixed `COLOR_`).
- Recursion guards (`self._updating_*` boolean flags) prevent circular updates between UI widgets and the asset data model.

## Render Output

- Rendered videos → `renders/` directory
- Temporary scene file → `_studio_temp.py` (auto-deleted after render)
- Quality options: Draft / HD / Full HD / 4K (passed as Manim CLI flags)
