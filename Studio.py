import sys
import json
import math
import copy
from pathlib import Path
from collections import deque
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
                             QSlider, QLabel, QComboBox, QTextEdit, QFileDialog,
                             QProgressBar, QFrame, QSplitter, QGroupBox, QFormLayout,
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                             QGraphicsPixmapItem, QGraphicsItem, QCheckBox, QTabWidget,
                             QScrollArea, QToolButton, QSpinBox, QMenu, QGraphicsObject,
                             QGraphicsDropShadowEffect, QDoubleSpinBox, QSizePolicy)
from PySide6.QtCore import (Qt, QThread, Signal, QRectF, QPointF, QSize, Property,
                            QPropertyAnimation, QEasingCurve, QTimer, QPoint)
from PySide6.QtGui import (QFont, QColor, QBrush, QPen, QPixmap, QDragEnterEvent,
                           QDropEvent, QPainter, QLinearGradient, QRadialGradient,
                           QAction, QPolygon, QKeySequence)
from PySide6.QtSvg import QSvgRenderer

from studio_core import StudioCore, PROJECT_ROOT

# --- PROFESSIONAL DESIGN SYSTEM ---
COLOR_BG_DARK = "#0b1220"
COLOR_BG_LIGHT = "#121a2a"
COLOR_PANEL = "rgba(20, 25, 35, 0.35)"  # Liquid Glass Token
COLOR_ACCENT = "#00d2ff"
COLOR_ACCENT_DIM = "rgba(0, 210, 255, 0.12)"
COLOR_TEXT_PRIMARY = "#f5f5f7"
COLOR_TEXT_SECONDARY = "#8b949e"
COLOR_BORDER = "rgba(255, 255, 255, 0.08)"
COLOR_CANVAS = "#050507"

FONT_MAIN = "Inter"
FONT_MONO = "JetBrains Mono"

GRID_8 = 8  # Strict 8px spacing grid

MANIM_WIDTH = 14.22
MANIM_HEIGHT = 8.0
CANVAS_SCALE = 56.25  # Pixel-to-Unit scale (450 / 8.0 = 56.25)

FPS = 30

TRACK_COLORS = [
    QColor(0, 210, 255, 180),
    QColor(255, 80, 180, 180),
    QColor(80, 255, 140, 180),
    QColor(255, 200, 50, 180),
    QColor(180, 80, 255, 180),
    QColor(255, 140, 50, 180),
]


class AnimatedButton(QPushButton):
    """A button with smooth hover scaling and depth effects."""
    def __init__(self, text, parent=None, is_accent=False):
        super().__init__(text, parent)
        self.is_accent = is_accent
        self._scale = 1.0

        self._anim = QPropertyAnimation(self, b"scale")
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setGraphicsEffect(None)  # Removed heavy shadows

    @Property(float)
    def scale(self): return self._scale

    @scale.setter
    def scale(self, s):
        self._scale = s
        self.update()

    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setEndValue(1.05)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Apply scaling from center
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width() / 2, -self.height() / 2)

        # Draw background based on accent
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self.is_accent:
            grad = QLinearGradient(0, 0, self.width(), 0)
            grad.setColorAt(0, QColor(COLOR_ACCENT))
            grad.setColorAt(1, QColor("#0099ff"))
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
        else:
            painter.setBrush(QColor(COLOR_BG_LIGHT))
            painter.setPen(QPen(QColor(COLOR_BORDER), 1))

        painter.drawRoundedRect(rect, 8, 8)

        # Text
        painter.setPen(QColor("#000000" if self.is_accent else COLOR_TEXT_PRIMARY))

        # Font point size safety
        font = self.font()
        size = font.pointSize()
        size = max(8, int(size))
        font.setPointSize(size)
        painter.setFont(font)

        painter.drawText(self.rect(), Qt.AlignCenter, self.text())
        painter.restore()
        painter.end()


class LayerWidget(QWidget):
    visibility_toggled = Signal(int, bool)
    lock_toggled = Signal(int, bool)

    def __init__(self, name, svg_path, index, parent=None):
        super().__init__(parent)
        self.index = index
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(48, 48)
        self.thumb.setStyleSheet(
            f"background: {COLOR_BG_DARK}; border-radius: 4px; border: 1px solid {COLOR_BORDER};"
        )

        renderer = QSvgRenderer(svg_path)
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        self.thumb.setPixmap(pixmap)

        layout.addWidget(self.thumb)

        # Metadata
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-weight: bold; font-family: {FONT_MAIN}; color: #ffffff;")
        path_lbl = QLabel(Path(svg_path).stem)
        path_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;")
        meta_layout.addWidget(name_lbl)
        meta_layout.addWidget(path_lbl)
        layout.addLayout(meta_layout)

        layout.addStretch()

        # Visibility toggle button
        self.vis_btn = QPushButton("👁")
        self.vis_btn.setCheckable(True)
        self.vis_btn.setChecked(True)
        self.vis_btn.setFixedSize(24, 24)
        self.vis_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 12px; padding: 0; }"
            "QPushButton:!checked { opacity: 0.3; color: gray; }"
        )
        self.vis_btn.clicked.connect(self._on_vis_clicked)
        layout.addWidget(self.vis_btn)

        # Lock toggle button
        self.lock_btn = QPushButton("🔒")
        self.lock_btn.setCheckable(True)
        self.lock_btn.setChecked(False)
        self.lock_btn.setFixedSize(24, 24)
        self.lock_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 12px; padding: 0; }"
        )
        self.lock_btn.clicked.connect(self._on_lock_clicked)
        layout.addWidget(self.lock_btn)

        # Drag Handle (Visual only)
        handle = QLabel("⋮⋮")
        handle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 16px;")
        layout.addWidget(handle)

    def _on_vis_clicked(self, checked):
        self.visibility_toggled.emit(self.index, checked)

    def _on_lock_clicked(self, checked):
        self.lock_toggled.emit(self.index, checked)


class TimelinePanel(QWidget):
    time_changed = Signal(float)  # 0.0 to 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.assets = []
        self.current_t = 0.0
        self.selected_index = -1
        self._dragging = False
        self.setMinimumHeight(80)
        self.setMouseTracking(True)

    def sizeHint(self):
        ruler_h = 24
        track_h = 28
        padding = 8
        n = max(len(self.assets), 1)
        return QSize(600, ruler_h + n * track_h + padding)

    def get_total_duration(self):
        if not self.assets:
            return 10.0
        return max((a.get("delay", 0.0) + a.get("duration", 2.0) for a in self.assets), default=10.0) + 0.5

    def set_assets(self, assets, selected_index=-1):
        self.assets = assets
        self.selected_index = selected_index
        self.updateGeometry()
        self.update()

    def set_time(self, t: float):
        self.current_t = max(0.0, min(1.0, t))
        self.update()

    def _track_area_x(self):
        return 180

    def _t_from_x(self, x):
        track_x = self._track_area_x()
        w = self.width() - track_x
        if w <= 0:
            return 0.0
        return max(0.0, min(1.0, (x - track_x) / w))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        ruler_h = 24
        track_h = 28
        name_w = self._track_area_x()
        total_w = self.width()
        track_area_w = total_w - name_w
        total_dur = self.get_total_duration()

        # Background
        painter.fillRect(self.rect(), QColor(COLOR_BG_DARK))

        # --- RULER ---
        ruler_rect_qt = self.rect().adjusted(name_w, 0, 0, -(self.height() - ruler_h))
        painter.fillRect(name_w, 0, track_area_w, ruler_h, QColor(COLOR_BG_LIGHT))

        # Ruler tick marks and labels
        painter.setPen(QPen(QColor(COLOR_TEXT_SECONDARY), 1))
        font = QFont(FONT_MONO, 8)
        painter.setFont(font)

        # Major ticks every 2 seconds
        step_s = 2.0
        tick_count = int(total_dur / step_s) + 2
        for i in range(tick_count):
            t_s = i * step_s
            if t_s > total_dur:
                break
            frac = t_s / total_dur
            rx = int(name_w + frac * track_area_w)
            painter.drawLine(rx, ruler_h - 8, rx, ruler_h)
            if i % 1 == 0:
                painter.drawText(rx + 2, ruler_h - 10, f"{int(t_s)}s")

        # Minor ticks every 0.5s
        for i in range(int(total_dur / 0.5) + 2):
            t_s = i * 0.5
            if t_s > total_dur:
                break
            frac = t_s / total_dur
            rx = int(name_w + frac * track_area_w)
            painter.drawLine(rx, ruler_h - 4, rx, ruler_h)

        # --- TRACKS ---
        for idx, asset in enumerate(self.assets):
            y = ruler_h + idx * track_h
            is_selected = (idx == self.selected_index)

            # Track background
            if is_selected:
                bg_color = QColor(40, 55, 75, 180)
            elif idx % 2 == 0:
                bg_color = QColor(18, 26, 42, 200)
            else:
                bg_color = QColor(14, 20, 34, 200)

            painter.fillRect(0, y, total_w, track_h, bg_color)

            # Asset name (left column)
            painter.setPen(QColor(COLOR_TEXT_PRIMARY if is_selected else COLOR_TEXT_SECONDARY))
            name_font = QFont(FONT_MAIN, 9)
            if is_selected:
                name_font.setBold(True)
            painter.setFont(name_font)
            name_str = asset.get("name", "?")[:20]
            painter.drawText(8, y + 4, name_w - 16, track_h - 8, Qt.AlignVCenter | Qt.AlignLeft, name_str)

            # Duration bar
            delay = asset.get("delay", 0.0)
            duration = asset.get("duration", 2.0)
            bar_start = delay / total_dur
            bar_end = (delay + duration) / total_dur
            bar_x = int(name_w + bar_start * track_area_w)
            bar_w = max(4, int((bar_end - bar_start) * track_area_w))
            bar_y = y + 6
            bar_h = track_h - 12

            color = TRACK_COLORS[idx % len(TRACK_COLORS)]
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

            # Easing label inside bar if wide enough
            if bar_w > 40:
                painter.setPen(QColor(0, 0, 0, 180))
                label_font = QFont(FONT_MONO, 7)
                painter.setFont(label_font)
                anim_str = asset.get("anim", "")
                painter.drawText(bar_x + 4, bar_y, bar_w - 8, bar_h, Qt.AlignVCenter | Qt.AlignLeft, anim_str)

        # Track area bottom border
        total_track_h = ruler_h + len(self.assets) * track_h
        painter.setPen(QPen(QColor(COLOR_BORDER), 1))
        painter.drawLine(0, total_track_h, total_w, total_track_h)

        # --- PLAYHEAD ---
        if track_area_w > 0:
            ph_x = int(name_w + self.current_t * track_area_w)
            # Line
            painter.setPen(QPen(QColor("#ffffff"), 1.5))
            painter.drawLine(ph_x, ruler_h, ph_x, self.height())
            # Triangle at top
            tri_size = 6
            tri_pts = QPolygon([
                QPoint(ph_x, ruler_h),
                QPoint(ph_x - tri_size, ruler_h - tri_size * 2),
                QPoint(ph_x + tri_size, ruler_h - tri_size * 2),
            ])
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(tri_pts)

        painter.end()

    def mousePressEvent(self, event):
        if event.x() > self._track_area_x():
            self._dragging = True
            t = self._t_from_x(event.x())
            self.time_changed.emit(t)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            t = self._t_from_x(event.x())
            self.time_changed.emit(t)

    def mouseReleaseEvent(self, event):
        self._dragging = False


class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setText(f"▶ {title}")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.setStyleSheet(f"""
            QToolButton {{
                background: {COLOR_BG_LIGHT}; border: none; border-bottom: 1px solid {COLOR_BORDER};
                color: {COLOR_ACCENT}; font-weight: bold; font-size: 11px;
                padding: 8px; text-align: left;
            }}
            QToolButton:checked {{ border-bottom: none; }}
        """)
        self.toggle_btn.clicked.connect(self.on_toggle)

        self.content = QWidget()
        self.content.setVisible(False)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(24, 24, 24, 24)  # Professional Breathability
        self.content_layout.setSpacing(12)  # Consistent Vertical Rhythm

        self.main_layout.addWidget(self.toggle_btn)
        self.main_layout.addWidget(self.content)

    def on_toggle(self):
        checked = self.toggle_btn.isChecked()
        self.content.setVisible(checked)
        self.toggle_btn.setText(f"{'▼' if checked else '▶'} {self.title}")
        if hasattr(self, "app_parent"):
            self.app_parent.update_interaction_mode()

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class StartHandle(QGraphicsRectItem):
    """A small handle to control the Start Position of an animation."""
    def __init__(self, parent):
        super().__init__(-6, -6, 12, 12, parent)
        self.setBrush(QBrush(QColor(COLOR_ACCENT)))
        self.setPen(QPen(QColor("#ffffff"), 1))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.SizeAllCursor)
        self.main_item = parent

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Update INITIAL state position
            manim_x = round((value.x() / CANVAS_SCALE) + self.main_item.asset["final_state"]["x"], 2)
            manim_y = round((-value.y() / CANVAS_SCALE) + self.main_item.asset["final_state"]["y"], 2)
            self.main_item.asset["initial_state"]["x"] = manim_x
            self.main_item.asset["initial_state"]["y"] = manim_y
            self.main_item.app.update_ui_from_asset()
            self.main_item.app.update_code()
            self.main_item.update()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        # Hide entirely in cinematic preview OR if not in Motion mode
        is_preview = self.main_item.app.canvas.preview_mode
        active_tab = self.main_item.app.get_active_inspector_section()
        if is_preview or active_tab != "MOTION":
            return

        painter.save()
        # Draw pivot point
        painter.setBrush(QColor(COLOR_ACCENT))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-3, -3, 6, 6)
        painter.restore()


class DraggableSVGItem(QGraphicsObject):
    """A visual representation of an SVG asset on the canvas."""
    def __init__(self, asset_data, parent_app, index):
        super().__init__()
        self.asset = asset_data
        self.app = parent_app
        self.index = index
        self._rect = QRectF(-50, -50, 100, 100)
        self._block_recursion = False

        # Entrance Animation
        self.setOpacity(0.0)
        self._anim = QPropertyAnimation(self, b"opacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        self.renderer = QSvgRenderer(self.asset["path"])
        if not self.renderer.isValid():
            print(f"Error: Invalid SVG file at {self.asset['path']}")
            self._rect = QRectF(-50, -50, 100, 100)
        else:
            bounds = self.renderer.viewBox()
            aspect = bounds.width() / bounds.height() if bounds.height() != 0 else 1
            if aspect > 1:
                w, h = 100, 100 / aspect
            else:
                w, h = 100 * aspect, 100
            self._rect = QRectF(-w / 2, -h / 2, w, h)

        self.setFlags(QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemIsFocusable |
                      QGraphicsItem.ItemSendsGeometryChanges)

        self._pen = QPen(QColor(COLOR_BORDER), 1)
        self._brush = QBrush(QColor(40, 40, 45, 50))
        self.setCacheMode(QGraphicsItem.NoCache)  # FIX: Disable caching

        self.handle = StartHandle(self)
        self.update_appearance()

    def set_locked(self, locked):
        self.setFlag(QGraphicsItem.ItemIsMovable, not locked)
        self.setFlag(QGraphicsItem.ItemIsSelectable, not locked)

    def boundingRect(self):
        return self._rect.adjusted(-2, -2, 2, 2)

    def update_pen(self):
        color = QColor(COLOR_ACCENT) if self.isSelected() else QColor(COLOR_BORDER)
        width = 2.5 if self.isSelected() else 1
        self._pen = QPen(color, width)
        self.update()

    def update_appearance(self):
        if self._block_recursion:
            return
        self._block_recursion = True
        try:
            # Final State is the base transform of the item
            final = self.asset["final_state"]
            self.setScale(final["scale"])
            self.setRotation(final["rotation"])

            px = final["x"] * CANVAS_SCALE
            py = -final["y"] * CANVAS_SCALE
            self.setPos(px, py)

            # Initial State is the handle position (offset from item center)
            initial = self.asset["initial_state"]
            sx = initial["x"] * CANVAS_SCALE - px
            sy = -initial["y"] * CANVAS_SCALE - py
            self.handle.setPos(sx, sy)
        finally:
            self._block_recursion = False

    def get_interpolated_state(self, t):
        easing_type = self.asset.get("easing", "Smooth")

        def lerp(a, b, t): return a + (b - a) * t

        def ease(t, mode):
            if mode == "Linear": return t
            if mode == "InExpo": return pow(2, 10 * (t - 1)) if t > 0 else 0
            if mode == "Elastic": return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * 2 * math.pi / 3) + 1
            if mode == "EaseOut": return 1 - (1 - t) * (1 - t)
            return t * t * (3 - 2 * t)  # Smooth

        it = ease(t, easing_type)
        init = self.asset["initial_state"]
        final = self.asset["final_state"]

        state = {
            "x": lerp(init["x"], final["x"], it),
            "y": lerp(init["y"], final["y"], it),
            "scale": lerp(init["scale"], final["scale"], it),
            "rotation": lerp(init["rotation"], final["rotation"], it),
            "opacity": lerp(init.get("opacity", 1.0), final.get("opacity", 1.0), it)
        }
        return state

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.app and not self._block_recursion:
            self.app.on_canvas_item_moved(self, value)
        if change == QGraphicsItem.ItemSelectedChange:
            self.update_pen()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        painter.save()

        # Visibility check — early exit if hidden
        if not self.asset.get("visible", True):
            painter.restore()
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 1. Context Analysis
        is_preview = self.app.canvas.preview_mode
        active_mode = self.app.get_active_inspector_section()
        is_selected = self.isSelected()
        if is_preview:
            # Cinematic Mode: Body Only
            scrubber_t = self.app.current_t
            state = self.get_interpolated_state(scrubber_t)

            # Manim Units -> Pixel Mapping
            tx = state["x"] * CANVAS_SCALE
            ty = -state["y"] * CANVAS_SCALE

            # Item's pos() is at final_state; translate relative to that
            final = self.asset["final_state"]
            fx = final["x"] * CANVAS_SCALE
            fy = -final["y"] * CANVAS_SCALE

            painter.save()
            painter.translate(tx - fx, ty - fy)
            painter.rotate(state["rotation"])
            painter.scale(state["scale"], state["scale"])
            painter.setOpacity(state["opacity"])
            self.renderer.render(painter, self._rect)
            painter.restore()
            painter.restore()
            return

        # Technical Editor Logic
        mode_motion = (active_mode == "MOTION") and is_selected
        mode_transform = (active_mode == "TRANSFORM") and is_selected

        final = self.asset["final_state"]
        fx = final["x"] * CANVAS_SCALE
        fy = -final["y"] * CANVAS_SCALE

        # 2. In edit mode the body ALWAYS renders at final_state so the
        #    Qt hitbox (pos()) and the visual stay perfectly aligned.
        #    Scrubber interpolation is only shown in preview mode (above).
        painter.save()
        # No translation needed — item.pos() is already at final_state
        painter.rotate(final["rotation"])
        painter.scale(final["scale"], final["scale"])
        painter.setOpacity(final.get("opacity", 1.0))

        # Render SVG Body
        self.renderer.render(painter, self._rect)

        # Transform Selection Box (Only in Transform Mode)
        if mode_transform:
            painter.setPen(QPen(QColor(COLOR_ACCENT), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self._rect)

        painter.restore()

        # 3. Motion Path Rendering (Only in Motion Mode)
        if mode_motion:
            painter.save()
            # Path goes from initial to final
            init = self.asset["initial_state"]
            final = self.asset["final_state"]

            # Pixel coords
            isx = init["x"] * CANVAS_SCALE
            isy = -init["y"] * CANVAS_SCALE
            fsx = final["x"] * CANVAS_SCALE
            fsy = -final["y"] * CANVAS_SCALE

            # Path Logic (Dashed line with arrow)
            gradient = QLinearGradient(isx, isy, fsx, fsy)
            gradient.setColorAt(0, QColor(COLOR_ACCENT))

            color = QColor(COLOR_ACCENT)
            color.setAlpha(50)
            gradient.setColorAt(1, color)

            pen = QPen(QBrush(gradient), 1.5, Qt.PenStyle.DashLine)
            pen.setDashOffset(self.app.animation_offset)
            painter.setPen(pen)
            painter.drawLine(QPointF(isx, isy), QPointF(fsx, fsy))

            # Arrowhead at Final
            angle = math.atan2(fsy - isy, fsx - isx)
            arrow_size = 10
            p1 = QPointF(fsx, fsy)
            p2 = QPointF(fsx - math.cos(angle - math.pi / 6) * arrow_size,
                         fsy - math.sin(angle - math.pi / 6) * arrow_size)
            p3 = QPointF(fsx - math.cos(angle + math.pi / 6) * arrow_size,
                         fsy - math.sin(angle + math.pi / 6) * arrow_size)
            painter.setBrush(QBrush(QColor(COLOR_ACCENT)))
            painter.drawPolygon([p1, p2, p3])
            painter.restore()

        # Ghosting (Only in Motion Mode when selected)
        if mode_motion:
            for i in range(1, 6):
                t = i / 6.0
                g_state = self.get_interpolated_state(t)
                gx = g_state["x"] * CANVAS_SCALE - fx
                gy = -g_state["y"] * CANVAS_SCALE - fy

                painter.save()
                painter.translate(gx, gy)
                painter.rotate(g_state["rotation"])
                painter.scale(g_state["scale"], g_state["scale"])
                painter.setOpacity(0.08 + (t * 0.12))
                self.renderer.render(painter, self._rect)
                painter.restore()
        painter.restore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.app.delete_selected()
        super().keyPressEvent(event)


class ModeIndicator(QLabel):
    def __init__(self, parent=None):
        super().__init__("PREVIEW", parent)
        self.setStyleSheet(f"""
            background: {COLOR_ACCENT}; color: #000; font-weight: bold;
            font-size: 10px; padding: 4px 10px; border-radius: 4px;
        """)
        self.setFixedWidth(80)
        self.setAlignment(Qt.AlignCenter)
        self.move(20, 20)


class StudioCanvas(QGraphicsView):
    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setScene(QGraphicsScene(self))

        # Lock Scene to Exact Manim Aspect Ratio (Pixel Parity)
        self.scene().setSceneRect(-399.9375, -225, 799.875, 450)

        # Viewport Architecture: Cinematic Mode
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        # Interaction
        self.setDragMode(QGraphicsView.NoDrag)
        self.setStyleSheet("background: transparent; border: none;")

        # Cinematic Controls
        self.show_grid = False
        self.grid_opacity = 0.02
        self.preview_mode = False

        self.mode_badge = ModeIndicator(self)

        # Ambient Animation
        self._bg_phase = 0.0
        self._bg_anim = QPropertyAnimation(self, b"bg_phase")
        self._bg_anim.setDuration(12000)
        self._bg_anim.setStartValue(0.0)
        self._bg_anim.setEndValue(360.0)
        self._bg_anim.setLoopCount(-1)
        self._bg_anim.start()

        self.setup_vignette()

    @Property(float)
    def bg_phase(self): return self._bg_phase

    @bg_phase.setter
    def bg_phase(self, v):
        self._bg_phase = v
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_to_stage()

    def setup_vignette(self):
        self.vignette = QGraphicsRectItem(-399.9375, -225, 799.875, 450)
        self.vignette.setZValue(1000)
        self.vignette.setFlag(QGraphicsItem.ItemHasNoContents, False)
        self.update_vignette()
        self.scene().addItem(self.vignette)

    def update_vignette(self):
        radial = QRadialGradient(0, 0, 500)
        radial.setColorAt(0, QColor(0, 0, 0, 0))
        radial.setColorAt(1, QColor(0, 0, 0, 80))
        self.vignette.setBrush(QBrush(radial))
        self.vignette.setPen(Qt.NoPen)
        self.vignette.setOpacity(0.4)

    def drawBackground(self, painter, rect):
        # 1. Base Deep Background
        painter.fillRect(rect, QColor(COLOR_BG_DARK))

        # 2. Layered Ambient Atmospheric Gradients
        painter.setRenderHint(QPainter.Antialiasing)

        # Slow Oscillations for Organic Movement
        p1 = self._bg_phase
        p2 = self._bg_phase * 0.7 + 45
        p3 = self._bg_phase * 0.4 + 90

        # Layer A: Deep Indigo (Moving Center)
        painter.save()
        ix = math.sin(math.radians(p1)) * 150
        iy = math.cos(math.radians(p1)) * 100
        ind_grad = QRadialGradient(ix, iy, 1000)
        ind_grad.setColorAt(0, QColor(20, 30, 80, 40))
        ind_grad.setColorAt(1, Qt.transparent)
        painter.fillRect(rect, QBrush(ind_grad))
        painter.restore()

        # Layer B: Subtle Purple (Moving Opposite)
        painter.save()
        px = math.cos(math.radians(p2)) * 200
        py = math.sin(math.radians(p2)) * 120
        purp_grad = QRadialGradient(px, py, 900)
        purp_grad.setColorAt(0, QColor(80, 20, 100, 30))
        purp_grad.setColorAt(1, Qt.transparent)
        painter.fillRect(rect, QBrush(purp_grad))
        painter.restore()

        # Layer C: Top-Left Soft Glow (Cyan Accent)
        painter.save()
        cx = -300 + math.sin(math.radians(p3)) * 50
        cy = -200 + math.cos(math.radians(p3)) * 40
        cyan_grad = QRadialGradient(cx, cy, 600)
        cyan_grad.setColorAt(0, QColor(0, 210, 255, 25))
        cyan_grad.setColorAt(1, Qt.transparent)
        painter.fillRect(rect, QBrush(cyan_grad))
        painter.restore()

        if self.show_grid and not self.preview_mode:
            painter.setPen(QPen(QColor(255, 255, 255, int(self.grid_opacity * 255)), 0.5))
            grid_size = 50
            for x in range(-400, 401, grid_size):
                painter.drawLine(x, -225, x, 225)
            for y in range(-225, 226, grid_size):
                painter.drawLine(-400, y, 400, y)

        # Stage Frame
        if not self.preview_mode:
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            painter.drawRect(-399.9375, -225, 799.875, 450)

    def drawForeground(self, painter, rect):
        # Cinematic Dimming outside Stage Area
        painter.save()
        from PySide6.QtGui import QRegion
        full_rect = rect.toRect()
        stage_rect = QRectF(-399.9375, -225, 799.875, 450).toRect()

        dim_region = QRegion(full_rect) - QRegion(stage_rect)
        painter.setClipRegion(dim_region)
        painter.fillRect(rect, QColor(0, 0, 0, 160))
        painter.restore()

    def wheelEvent(self, event):
        # Disabled for strict viewport lock
        pass

    def fit_to_stage(self):
        self.fitInView(QRectF(-399.9375, -225, 799.875, 450), Qt.KeepAspectRatio)
        if hasattr(self, "app"):
            scale_val = int(self.transform().m11() * 100)
            self.app.zoom_lbl.setText(f"{scale_val}%")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(".svg"):
                self.file_dropped.emit(file_path)


class RenderThread(QThread):
    finished = Signal(bool)
    log_signal = Signal(str)

    def __init__(self, global_params, assets, quality):
        super().__init__()
        self.global_params = global_params
        self.assets = assets
        self.quality = quality

    def run(self):
        success = StudioCore.run_render(self.global_params, self.assets, self.quality, self.log_signal.emit)
        self.finished.emit(success)


class SVGStudioWYSIWYG(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MorphStudio – Vector Motion Engine")
        self.resize(1500, 950)

        # 1. CORE STATE INITIALIZATION (Must happen before UI)
        self.assets = []
        self.canvas_items = []
        self.selected_index = -1
        self.initializing = True
        self._block_recursion = False
        self.animation_offset = 0
        self.current_t = 0.0
        self.is_playing = False
        self.history = deque(maxlen=50)
        self.redo_stack = []
        self._updating_xy = False

        # 2. UI SETUP
        app_font = QFont(FONT_MAIN, 11)
        app_font.setHintingPreference(QFont.PreferVerticalHinting)
        self.setFont(app_font)

        self.setup_ui()
        self.apply_styles()
        self.initializing = False

        # 3. PROFESSIONAL STARTUP ANIMATION
        self.setWindowOpacity(0.0)
        self._bloom = QPropertyAnimation(self, b"windowOpacity")
        self._bloom.setDuration(800)
        self._bloom.setStartValue(0.0)
        self._bloom.setEndValue(1.0)
        self._bloom.setEasingCurve(QEasingCurve.OutCubic)
        self._bloom.start()

        # Animation loop for path dash offset
        self.dash_timer = QTimer(self)
        self.dash_timer.timeout.connect(self.animate_path)
        self.dash_timer.start(50)

        self.update_code()

        # Initial Fit
        QTimer.singleShot(100, self.canvas.fit_to_stage)

    def animate_path(self):
        self.animation_offset -= 2
        if self.selected_index >= 0:
            self.canvas_items[self.selected_index].update()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.top_layout = QVBoxLayout(self.central_widget)
        self.top_layout.setContentsMargins(GRID_8 * 2, GRID_8 * 2, GRID_8 * 2, GRID_8 * 2)
        self.top_layout.setSpacing(GRID_8 * 2)

        # --- FILE MENU ---
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        act_new = QAction("New Project", self)
        act_new.setShortcut(QKeySequence("Ctrl+N"))
        act_new.triggered.connect(self.clear_canvas)
        act_open = QAction("Open Project...", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self.load_project)
        act_save = QAction("Save Project...", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self.save_project)
        file_menu.addAction(act_new)
        file_menu.addAction(act_open)
        file_menu.addAction(act_save)

        # --- BRAND BAR ---
        self.brand_bar = QFrame()
        self.brand_bar.setFixedHeight(64)
        self.brand_bar.setObjectName("BrandBar")
        self.brand_bar.setStyleSheet(f"""
            #BrandBar {{
                background: rgba(255, 255, 255, 0.03);
                border-bottom: 1px solid {COLOR_BORDER};
            }}
        """)
        bb_layout = QHBoxLayout(self.brand_bar)
        bb_layout.setContentsMargins(GRID_8 * 3, 0, GRID_8 * 3, 0)
        bb_layout.setSpacing(GRID_8 * 1.5)

        self.brand_icon = QLabel("◈")
        self.brand_icon.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 24px; font-weight: bold;")

        self.brand_text_container = QWidget()
        self.brand_text_vbox = QVBoxLayout(self.brand_text_container)
        self.brand_text_vbox.setContentsMargins(0, 0, 0, 0)
        self.brand_text_vbox.setSpacing(0)

        self.brand_title = QLabel("MorphStudio")
        self.brand_title.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-size: 18px; font-weight: 600; letter-spacing: 0.5px;"
        )

        self.brand_subtitle = QLabel("Vector Motion Engine")
        self.brand_subtitle.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px; font-weight: 300; "
            f"text-transform: uppercase; letter-spacing: 1.5px;"
        )

        self.brand_text_vbox.addWidget(self.brand_title)
        self.brand_text_vbox.addWidget(self.brand_subtitle)

        bb_layout.addWidget(self.brand_icon)
        bb_layout.addWidget(self.brand_text_container)
        bb_layout.addStretch()

        self.top_layout.addWidget(self.brand_bar)

        # Main Work Area
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(GRID_8 * 2)
        self.top_layout.addLayout(self.main_layout)

        # --- LEFT SIDEBAR (Layers) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(280)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(GRID_8 * 2, GRID_8 * 2, GRID_8 * 2, GRID_8 * 2)
        self.sidebar_layout.setSpacing(GRID_8 * 1.5)

        self.layer_header = QLabel("LAYERS")
        self.layer_header.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 10px; letter-spacing: 1px;"
        )
        self.sidebar_layout.addWidget(self.layer_header)

        self.sidebar_divider = QFrame()
        self.sidebar_divider.setFixedHeight(1)
        self.sidebar_divider.setStyleSheet(f"background: {COLOR_BORDER};")
        self.sidebar_layout.addWidget(self.sidebar_divider)

        self.layer_list = QListWidget()
        self.layer_list.itemClicked.connect(self.select_by_index)
        self.layer_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layer_list.customContextMenuRequested.connect(self.show_layer_context_menu)
        self.layer_list.setDragDropMode(QListWidget.InternalMove)
        self.layer_list.model().rowsMoved.connect(self.on_layer_reordered)
        self.sidebar_layout.addWidget(self.layer_list)

        self.add_btn = AnimatedButton("IMPORT SVG")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.clicked.connect(self.import_dialog)
        self.sidebar_layout.addWidget(self.add_btn)

        self.clear_btn = AnimatedButton("CLEAR ALL")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.setObjectName("DeleteButton")
        self.clear_btn.clicked.connect(self.clear_canvas)
        self.sidebar_layout.addWidget(self.clear_btn)

        self.sidebar_layout.addStretch()

        l_shadow = QGraphicsDropShadowEffect()
        l_shadow.setBlurRadius(25)
        l_shadow.setColor(QColor(0, 0, 0, 150))
        l_shadow.setOffset(5, 0)
        self.sidebar.setGraphicsEffect(l_shadow)

        self.main_layout.addWidget(self.sidebar)

        # 2. Center Column
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(GRID_8 * 2)

        # --- STAGE CONTAINER ---
        self.stage_box = QFrame()
        self.stage_box.setObjectName("StageBox")
        self.sb_layout = QVBoxLayout(self.stage_box)
        self.sb_layout.setContentsMargins(GRID_8 * 2, GRID_8 * 2, GRID_8 * 2, GRID_8 * 2)

        self.preview_overlay = QLabel("MorphStudio Preview")
        self.preview_overlay.setAlignment(Qt.AlignCenter)
        self.preview_overlay.setStyleSheet(
            "color: rgba(255, 255, 255, 0.3); font-size: 10px; font-weight: 300; "
            "letter-spacing: 2px; text-transform: uppercase;"
        )
        self.sb_layout.addWidget(self.preview_overlay)

        self.canvas = StudioCanvas()
        self.canvas.app = self
        self.canvas.file_dropped.connect(self.add_svg_asset)
        self.canvas.scene().selectionChanged.connect(self.on_selection_changed)
        self.sb_layout.addWidget(self.canvas, alignment=Qt.AlignCenter)

        center_layout.addStretch(1)
        center_layout.addWidget(self.stage_box, alignment=Qt.AlignCenter)

        # --- TRANSPORT BAR ---
        self.transport_bar = QFrame()
        self.transport_bar.setStyleSheet(
            f"background: {COLOR_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;"
        )
        tr_layout = QHBoxLayout(self.transport_bar)
        tr_layout.setContentsMargins(12, 4, 12, 4)
        tr_layout.setSpacing(8)

        self.btn_rewind = QPushButton("⏮")
        self.btn_rewind.setFixedSize(28, 28)
        self.btn_rewind.clicked.connect(self.rewind)

        self.btn_play = QPushButton("▶")
        self.btn_play.setCheckable(True)
        self.btn_play.setFixedSize(32, 28)
        self.btn_play.clicked.connect(self.toggle_play)

        self.time_label = QLabel("0.00s")
        self.time_label.setFixedWidth(60)
        self.time_label.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-family: '{FONT_MONO}'; font-size: 11px;"
        )
        self.time_label.setAlignment(Qt.AlignCenter)

        tr_layout.addWidget(self.btn_rewind)
        tr_layout.addWidget(self.btn_play)
        tr_layout.addWidget(self.time_label)
        tr_layout.addStretch()

        self.btn_loop = QPushButton("🔁")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setChecked(True)
        self.btn_loop.setFixedSize(28, 28)
        tr_layout.addWidget(self.btn_loop)

        center_layout.addWidget(self.transport_bar)

        # --- TIMELINE PANEL ---
        self.timeline_panel = TimelinePanel()
        self.timeline_panel.time_changed.connect(self.on_timeline_changed)

        tl_scroll = QScrollArea()
        tl_scroll.setWidget(self.timeline_panel)
        tl_scroll.setWidgetResizable(True)
        tl_scroll.setFixedHeight(140)
        tl_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tl_scroll.setFrameShape(QFrame.NoFrame)
        tl_scroll.setStyleSheet("background: transparent;")

        center_layout.addWidget(tl_scroll)

        # Play timer
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(int(1000 / FPS))
        self.play_timer.timeout.connect(self._advance_frame)

        # --- CANVAS TOOLBAR ---
        self.toolbar_container = QWidget()
        tb_layout = QHBoxLayout(self.toolbar_container)
        tb_layout.setContentsMargins(0, 0, 0, 0)

        t_bar = QFrame()
        t_bar.setStyleSheet(
            f"background: {COLOR_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 16px;"
        )
        t_bar_layout = QHBoxLayout(t_bar)
        t_bar_layout.setContentsMargins(8, 4, 8, 4)
        t_bar_layout.setSpacing(8)

        self.grid_toggle = QPushButton("🌐")
        self.grid_toggle.setCheckable(True)
        self.grid_toggle.setChecked(False)
        self.grid_toggle.setFixedSize(28, 28)
        self.grid_toggle.clicked.connect(self.toggle_grid)
        t_bar_layout.addWidget(self.grid_toggle)

        self.btn_fit = QPushButton("📺")
        self.btn_fit.setFixedSize(28, 28)
        self.btn_fit.clicked.connect(self.canvas.fit_to_stage)
        t_bar_layout.addWidget(self.btn_fit)

        self.btn_preview = QPushButton("🎬")
        self.btn_preview.setCheckable(True)
        self.btn_preview.setFixedSize(28, 28)
        self.btn_preview.clicked.connect(self.toggle_preview_mode)
        t_bar_layout.addWidget(self.btn_preview)

        tb_layout.addWidget(t_bar)
        tb_layout.addStretch()

        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: bold;"
        )
        tb_layout.addWidget(self.zoom_lbl)

        center_layout.addWidget(self.toolbar_container)

        # 3. Bottom Tabs: Console & Code
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setFixedHeight(160)
        self.bottom_tabs.setObjectName("BottomPanel")

        # Console
        self.console_panel = QFrame()
        console_layout = QVBoxLayout(self.console_panel)
        console_layout.setContentsMargins(8, 8, 8, 8)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont(FONT_MONO, 10))
        console_layout.addWidget(self.console)
        self.bottom_tabs.addTab(self.console_panel, "CONSOLE")

        # Code Preview
        self.code_panel = QFrame()
        code_layout = QVBoxLayout(self.code_panel)
        code_layout.setContentsMargins(8, 8, 8, 8)
        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setFont(QFont(FONT_MONO, 10))
        code_layout.addWidget(self.code_view)
        self.bottom_tabs.addTab(self.code_panel, "CODE")

        center_layout.addWidget(self.bottom_tabs)

        self.main_layout.addWidget(center_widget, stretch=1)

        # --- RIGHT SIDEBAR: INSPECTOR ---
        self.inspector_panel = QFrame()
        self.inspector_panel.setFixedWidth(320)
        self.inspector_panel.setObjectName("Inspector")
        self.insp_layout = QVBoxLayout(self.inspector_panel)
        self.insp_layout.setContentsMargins(0, 0, 0, 0)
        self.insp_layout.setSpacing(0)

        self.insp_header = QLabel("PROPERTIES")
        self.insp_header.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 10px; "
            f"letter-spacing: 1.5px; padding: 24px;"
        )
        self.insp_layout.addWidget(self.insp_header)

        self.insp_divider = QFrame()
        self.insp_divider.setFixedHeight(1)
        self.insp_divider.setStyleSheet(f"background: {COLOR_BORDER};")
        self.insp_layout.addWidget(self.insp_divider)

        self.insp_scroll = QScrollArea()
        self.insp_scroll.setWidgetResizable(True)
        self.insp_scroll.setFrameShape(QFrame.NoFrame)
        self.insp_content = QWidget()
        self.inspector_layout = QVBoxLayout(self.insp_content)
        self.inspector_layout.setContentsMargins(0, 0, 0, 0)
        self.inspector_layout.setSpacing(0)
        self.insp_scroll.setWidget(self.insp_content)
        self.insp_layout.addWidget(self.insp_scroll)

        # Section 1: TRANSFORM
        self.trans_section = CollapsibleSection("TRANSFORM")
        self.trans_section.app_parent = self
        self.trans_form = QFormLayout()
        self.trans_form.setSpacing(12)
        self.scale_slider = self.create_slider("Scale", 10, 500, 100, self.trans_form)
        self.rot_slider = self.create_slider("Rotation", -360, 360, 0, self.trans_form)

        # X/Y Position spinboxes
        xy_widget = QWidget()
        xy_layout = QHBoxLayout(xy_widget)
        xy_layout.setContentsMargins(0, 0, 0, 0)
        xy_layout.setSpacing(6)

        x_lbl = QLabel("X")
        x_lbl.setFixedWidth(12)
        x_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;")
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-7.11, 7.11)
        self.x_spin.setSingleStep(0.1)
        self.x_spin.setDecimals(2)
        self.x_spin.setFixedWidth(72)
        self.x_spin.setStyleSheet(
            f"background: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: 4px; padding: 2px; color: {COLOR_TEXT_PRIMARY};"
        )

        y_lbl = QLabel("Y")
        y_lbl.setFixedWidth(12)
        y_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;")
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-4.0, 4.0)
        self.y_spin.setSingleStep(0.1)
        self.y_spin.setDecimals(2)
        self.y_spin.setFixedWidth(72)
        self.y_spin.setStyleSheet(
            f"background: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: 4px; padding: 2px; color: {COLOR_TEXT_PRIMARY};"
        )

        self.x_spin.valueChanged.connect(self.on_xy_spin_changed)
        self.y_spin.valueChanged.connect(self.on_xy_spin_changed)

        xy_layout.addWidget(x_lbl)
        xy_layout.addWidget(self.x_spin)
        xy_layout.addSpacing(8)
        xy_layout.addWidget(y_lbl)
        xy_layout.addWidget(self.y_spin)
        xy_layout.addStretch()
        self.trans_form.addRow("Position", xy_widget)

        # Opacity slider
        self.opacity_slider = self.create_slider("Opacity", 0, 100, 100, self.trans_form)

        # Smart Tools
        tool_group = QGroupBox("SMART TOOLS")
        tool_layout = QVBoxLayout(tool_group)
        tool_layout.setContentsMargins(GRID_8, GRID_8, GRID_8, GRID_8)
        tool_layout.setSpacing(GRID_8)

        btn_center = QPushButton("🎯 CENTER TO STAGE")
        btn_center.setMinimumHeight(32)
        btn_center.clicked.connect(self.center_selected)
        tool_layout.addWidget(btn_center)

        btn_distribute = QPushButton("↔️ DISTRIBUTE HORIZONTALLY")
        btn_distribute.setMinimumHeight(32)
        btn_distribute.clicked.connect(self.distribute_selected)
        tool_layout.addWidget(btn_distribute)

        self.trans_form.addRow(tool_group)

        self.trans_section.addLayout(self.trans_form)

        # Section 2: MOTION
        self.motion_section = CollapsibleSection("MOTION")
        self.motion_section.app_parent = self
        self.motion_form = QFormLayout()
        self.motion_form.setSpacing(12)
        self.anim_combo = QComboBox()
        self.anim_combo.addItems(["Path", "Morph", "FlyIn", "PopIn", "Fade", "Draw"])
        self.anim_combo.currentIndexChanged.connect(self.on_anim_type_changed)
        self.motion_form.addRow("Mode", self.anim_combo)

        self.morph_target_btn = QPushButton("SELECT TARGET SVG...")
        self.morph_target_btn.setMinimumHeight(28)
        self.morph_target_btn.setVisible(False)
        self.morph_target_btn.clicked.connect(self.select_morph_target)
        self.motion_form.addRow(self.morph_target_btn)

        self.easing_combo = QComboBox()
        self.easing_combo.addItems(["Smooth", "Linear", "InExpo", "InBounce", "Elastic", "EaseOut", "EaseInOut"])
        self.easing_combo.currentIndexChanged.connect(self.sync_asset_to_ui)
        self.motion_form.addRow("Curve", self.easing_combo)

        self.delay_slider = self.create_slider("Delay", 0, 1000, 0, self.motion_form)
        self.dur_slider = self.create_slider("Duration", 50, 800, 200, self.motion_form)
        self.seq_check = QCheckBox("After Previous")
        self.seq_check.stateChanged.connect(self.sync_asset_to_ui)
        self.motion_form.addRow(self.seq_check)
        self.motion_section.addLayout(self.motion_form)

        # Section 3: STAGE
        self.stage_section = CollapsibleSection("STAGE")
        self.stage_section.app_parent = self
        self.stage_form = QFormLayout()
        self.stage_form.setSpacing(12)
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["#0a0a0c", "#ffffff", "#1e1e2e", "#000000"])
        self.bg_combo.currentIndexChanged.connect(self.on_bg_changed)
        self.stage_form.addRow("Stage", self.bg_combo)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Draft", "HD", "Full HD", "4K"])
        self.quality_mapping = {"Draft": "l", "HD": "m", "Full HD": "k", "4K": "p"}
        self.stage_form.addRow("Export", self.quality_combo)

        self.render_btn = AnimatedButton("RENDER STUDIO EXPORT", is_accent=True)
        self.render_btn.setMinimumHeight(48)
        self.render_btn.clicked.connect(self.start_render)
        self.stage_form.addRow(self.render_btn)

        self.stage_section.addLayout(self.stage_form)

        self.inspector_layout.addWidget(self.trans_section)
        self.inspector_layout.addWidget(self.motion_section)
        self.inspector_layout.addWidget(self.stage_section)
        self.inspector_layout.addStretch()

        self.main_layout.addWidget(self.inspector_panel)

    # -------------------------------------------------------------------------
    # Undo / Redo
    # -------------------------------------------------------------------------

    def push_undo(self):
        snapshot = copy.deepcopy(self.assets)
        self.history.append(snapshot)
        self.redo_stack.clear()

    def undo(self):
        if len(self.history) < 2:
            return
        self.redo_stack.append(self.history.pop())
        self._restore_snapshot(self.history[-1])

    def redo(self):
        if not self.redo_stack:
            return
        state = self.redo_stack.pop()
        self.history.append(state)
        self._restore_snapshot(state)

    def _restore_snapshot(self, snapshot):
        self.initializing = True
        self.canvas.scene().clear()
        self.canvas_items = []
        self.assets = []
        self.layer_list.clear()
        self.canvas.setup_vignette()
        for asset in snapshot:
            self.add_svg_asset_obj(copy.deepcopy(asset))
        self.initializing = False
        self.selected_index = -1
        self.timeline_panel.set_assets(self.assets)
        self.update_code()

    # -------------------------------------------------------------------------
    # Project Save / Load
    # -------------------------------------------------------------------------

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "MorphStudio Project (*.morphs)"
        )
        if not path:
            return
        data = {"version": 2, "assets": self.assets}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        self.console.append(f">>> Project saved: {Path(path).name}")

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "MorphStudio Project (*.morphs)"
        )
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            self.clear_canvas()
            for asset in data.get("assets", []):
                self.add_svg_asset_obj(asset)
            self.console.append(f">>> Loaded: {Path(path).name}")
        except Exception as e:
            self.console.append(f">>> Load error: {e}")

    # -------------------------------------------------------------------------
    # Playback
    # -------------------------------------------------------------------------

    def toggle_play(self, checked):
        self.is_playing = checked
        if checked:
            self.btn_play.setText("❚❚")
            if self.current_t >= 1.0:
                self.current_t = 0.0
            self.play_timer.start()
        else:
            self.btn_play.setText("▶")
            self.play_timer.stop()

    def _advance_frame(self):
        if not self.assets:
            return
        max_dur = max(a.get("duration", 2.0) for a in self.assets)
        step = 1.0 / (FPS * max(max_dur, 0.1))
        self.current_t += step
        if self.current_t >= 1.0:
            if self.btn_loop.isChecked():
                self.current_t = 0.0
            else:
                self.current_t = 1.0
                self.is_playing = False
                self.play_timer.stop()
                self.btn_play.setChecked(False)
                self.btn_play.setText("▶")
        self._sync_playhead()

    def rewind(self):
        self.current_t = 0.0
        self._sync_playhead()

    def _sync_playhead(self):
        self.timeline_panel.set_time(self.current_t)
        max_dur = max((a.get("duration", 2.0) for a in self.assets), default=2.0)
        self.time_label.setText(f"{self.current_t * max_dur:.2f}s")
        for item in self.canvas_items:
            item.update()

    def on_timeline_changed(self, t: float):
        self.current_t = t
        max_dur = max((a.get("duration", 2.0) for a in self.assets), default=2.0)
        self.time_label.setText(f"{self.current_t * max_dur:.2f}s")
        for item in self.canvas_items:
            item.update()

    # -------------------------------------------------------------------------
    # Inspector callbacks
    # -------------------------------------------------------------------------

    def on_xy_spin_changed(self):
        if self._updating_xy or self.selected_index < 0:
            return
        asset = self.assets[self.selected_index]
        dx = self.x_spin.value() - asset["final_state"]["x"]
        dy = self.y_spin.value() - asset["final_state"]["y"]
        asset["final_state"]["x"] = self.x_spin.value()
        asset["final_state"]["y"] = self.y_spin.value()
        asset["initial_state"]["x"] += dx
        asset["initial_state"]["y"] += dy
        item = self.canvas_items[self.selected_index]
        item.update_appearance()
        self.update_code()

    def on_asset_visibility_changed(self, index, visible):
        if 0 <= index < len(self.assets):
            self.assets[index]["visible"] = visible
            self.canvas_items[index].update()
            self.timeline_panel.set_assets(self.assets, self.selected_index)

    def on_asset_lock_changed(self, index, locked):
        if 0 <= index < len(self.assets):
            self.assets[index]["locked"] = locked
            self.canvas_items[index].set_locked(locked)

    def on_layer_reordered(self, parent, start, end, dest, row):
        # Rebuild assets/canvas_items order from list widget current order
        id_map = {id(a): (a, ci) for a, ci in zip(self.assets, self.canvas_items)}
        new_assets = []
        new_items = []
        for i in range(self.layer_list.count()):
            aid = self.layer_list.item(i).data(Qt.UserRole)
            if aid in id_map:
                a, ci = id_map[aid]
                new_assets.append(a)
                new_items.append(ci)
                ci.setZValue(i)
        self.assets = new_assets
        self.canvas_items = new_items
        self.selected_index = -1
        self.timeline_panel.set_assets(self.assets)
        self.update_code()

    # -------------------------------------------------------------------------
    # Existing methods (preserved + updated)
    # -------------------------------------------------------------------------

    def on_bg_changed(self, index):
        if not self.initializing:
            self.canvas.update()
            self.update_code()

    def create_slider(self, label, min_v, max_v, def_v, form):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(def_v)

        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(def_v)
        spin.setFixedWidth(54)
        spin.setAlignment(Qt.AlignRight)
        spin.setStyleSheet(
            f"background: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: 4px; padding: 2px;"
        )

        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        slider.valueChanged.connect(self.sync_asset_to_ui)

        layout.addWidget(slider)
        layout.addWidget(spin)

        form.addRow(label, container)
        return slider

    def create_sub_slider(self, form, label, min_v, max_v, def_v):
        return self.create_slider(label, min_v, max_v, def_v, form)

    def apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {COLOR_BG_DARK}; }}
            QWidget {{ color: {COLOR_TEXT_PRIMARY}; font-family: '{FONT_MAIN}', sans-serif; font-size: 12px; }}

            #Sidebar, #Inspector {{
                background: {COLOR_PANEL};
                border: 1px solid {COLOR_BORDER};
                border-radius: 16px;
                margin: {GRID_8}px;
            }}

            #BrandBar {{ border-bottom: 1px solid {COLOR_BORDER}; }}

            #StageBox {{
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}

            QMenuBar {{
                background: {COLOR_BG_DARK};
                color: {COLOR_TEXT_PRIMARY};
                border-bottom: 1px solid {COLOR_BORDER};
            }}
            QMenuBar::item:selected {{
                background: {COLOR_ACCENT_DIM};
                color: {COLOR_ACCENT};
            }}
            QMenu {{
                background: {COLOR_BG_LIGHT};
                border: 1px solid {COLOR_BORDER};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QMenu::item:selected {{
                background: {COLOR_ACCENT_DIM};
                color: {COLOR_ACCENT};
            }}

            QGroupBox {{ font-weight: 600; font-size: 10px; color: {COLOR_TEXT_SECONDARY};
                         border: none; margin-top: {GRID_8 * 2}px; padding-top: {GRID_8}px; }}

            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: {GRID_8}px {GRID_8 * 2}px;
                font-weight: 600;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-color: {COLOR_ACCENT};
            }}

            #RenderButton {{
                background: {COLOR_ACCENT};
                color: {COLOR_BG_DARK};
                border: none;
                padding: {GRID_8 * 1.5}px;
                font-size: 12px;
                letter-spacing: 0.5px;
                border-radius: 6px;
            }}
            #RenderButton:hover {{ background: #ffffff; }}

            QListWidget {{ background: transparent; border: none; }}
            QListWidget::item {{
                padding: {GRID_8}px;
                border-radius: 6px;
                margin-bottom: 4px;
                color: {COLOR_TEXT_SECONDARY};
                background: rgba(255, 255, 255, 0.02);
            }}
            QListWidget::item:hover {{ background: rgba(255, 255, 255, 0.05); }}
            QListWidget::item:selected {{ background: {COLOR_ACCENT_DIM}; color: {COLOR_ACCENT}; font-weight: 600; }}

            QComboBox {{ background: rgba(255, 255, 255, 0.05); border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 4px {GRID_8}px; }}

            QSlider::groove:horizontal {{ height: 2px; background: {COLOR_BORDER}; }}
            QSlider::handle:horizontal {{ background: {COLOR_ACCENT}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}

            QScrollBar:vertical {{ border: none; background: transparent; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {COLOR_BORDER}; border-radius: 2px; }}

            QTextEdit {{ background: rgba(0, 0, 0, 0.2); border: 1px solid {COLOR_BORDER}; border-radius: 8px; color: {COLOR_TEXT_SECONDARY}; padding: {GRID_8}px; }}

            QTabWidget::pane {{ border-top: 1px solid {COLOR_BORDER}; background: {COLOR_PANEL}; border-radius: 14px; margin: 0 {GRID_8}px; }}
            QTabBar::tab {{ background: transparent; padding: {GRID_8}px {GRID_8 * 2}px; color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 10px; }}
            QTabBar::tab:selected {{ color: {COLOR_ACCENT}; border-bottom: 2px solid {COLOR_ACCENT}; }}
        """)

    def import_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Import SVGs", "", "SVG Files (*.svg)")
        for f in files:
            self.add_svg_asset(f)

    def select_by_index(self, item_widget):
        self.selected_index = self.layer_list.row(item_widget)
        self.canvas.scene().clearSelection()
        if 0 <= self.selected_index < len(self.canvas_items):
            self.canvas_items[self.selected_index].setSelected(True)
            self.update_ui_from_asset()

    def on_selection_changed(self):
        selected = self.canvas.scene().selectedItems()
        if selected:
            for i, item in enumerate(self.canvas_items):
                if item == selected[0]:
                    self.selected_index = i
                    self.layer_list.setCurrentRow(i)
                    self.update_ui_from_asset()
                    break

    def on_canvas_item_moved(self, item, pos):
        if self._block_recursion:
            return
        self._block_recursion = True

        new_manim_x = round(pos.x() / CANVAS_SCALE, 2)
        new_manim_y = round(-pos.y() / CANVAS_SCALE, 2)

        try:
            idx = self.canvas_items.index(item)
            asset = self.assets[idx]

            old_final = asset["final_state"]
            dx = new_manim_x - old_final["x"]
            dy = new_manim_y - old_final["y"]

            asset["initial_state"]["x"] += dx
            asset["initial_state"]["y"] += dy
            asset["final_state"]["x"] = new_manim_x
            asset["final_state"]["y"] = new_manim_y

            self.update_code()

            initial = asset["initial_state"]
            hx = initial["x"] * CANVAS_SCALE - pos.x()
            hy = -initial["y"] * CANVAS_SCALE - pos.y()
            item.handle.setPos(hx, hy)

            item.update()

            # Update X/Y spinboxes
            self._updating_xy = True
            self.x_spin.blockSignals(True)
            self.y_spin.blockSignals(True)
            self.x_spin.setValue(asset["final_state"]["x"])
            self.y_spin.setValue(asset["final_state"]["y"])
            self.x_spin.blockSignals(False)
            self.y_spin.blockSignals(False)
            self._updating_xy = False

        except (ValueError, KeyError):
            pass
        finally:
            self._block_recursion = False

    def update_ui_from_asset(self):
        if self.selected_index < 0:
            return
        asset = self.assets[self.selected_index]
        initial = asset["initial_state"]
        final = asset["final_state"]

        for w in (self.scale_slider, self.rot_slider, self.delay_slider,
                  self.dur_slider, self.anim_combo, self.easing_combo, self.seq_check):
            w.blockSignals(True)

        self.scale_slider.setValue(int(final["scale"] * 100))
        self.rot_slider.setValue(final["rotation"])
        self.delay_slider.setValue(int(asset["delay"] * 100))
        self.dur_slider.setValue(int(asset["duration"] * 100))
        self.anim_combo.setCurrentText(asset["anim"])
        self.easing_combo.setCurrentText(asset["easing"])
        self.seq_check.setChecked(asset["sequence_mode"])

        for w in (self.scale_slider, self.rot_slider, self.delay_slider,
                  self.dur_slider, self.anim_combo, self.easing_combo, self.seq_check):
            w.blockSignals(False)

        # X/Y/Opacity
        self._updating_xy = True
        self.x_spin.blockSignals(True)
        self.y_spin.blockSignals(True)
        self.opacity_slider.blockSignals(True)
        self.x_spin.setValue(final["x"])
        self.y_spin.setValue(final["y"])
        self.opacity_slider.setValue(int(final.get("opacity", 1.0) * 100))
        self.x_spin.blockSignals(False)
        self.y_spin.blockSignals(False)
        self.opacity_slider.blockSignals(False)
        self._updating_xy = False

    def get_active_inspector_section(self):
        if self.motion_section.content.isVisible():
            return "MOTION"
        if self.trans_section.content.isVisible():
            return "TRANSFORM"
        return "PREVIEW"

    def update_interaction_mode(self):
        mode = self.get_active_inspector_section()
        self.canvas.mode_badge.setText(mode)
        self.canvas.update()
        for item in self.canvas_items:
            item.handle.update()
            item.update()

    def on_anim_type_changed(self):
        is_morph = self.anim_combo.currentText() == "Morph"
        self.morph_target_btn.setVisible(is_morph)
        self.sync_asset_to_ui()

    def select_morph_target(self):
        if self.selected_index < 0:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Morph Target", "", "SVG Files (*.svg)")
        if file_path:
            self.assets[self.selected_index]["final_state"]["svg"] = file_path.replace("\\", "/")
            self.update_code()
            self.canvas_items[self.selected_index].update()

    def sync_asset_to_ui(self):
        if self.selected_index < 0:
            return
        asset = self.assets[self.selected_index]
        asset["final_state"]["scale"] = self.scale_slider.value() / 100.0
        asset["final_state"]["rotation"] = self.rot_slider.value()
        asset["delay"] = self.delay_slider.value() / 100.0
        asset["duration"] = self.dur_slider.value() / 100.0
        asset["anim"] = self.anim_combo.currentText()
        asset["easing"] = self.easing_combo.currentText()
        asset["sequence_mode"] = self.seq_check.isChecked()
        asset["final_state"]["opacity"] = self.opacity_slider.value() / 100.0

        item = self.canvas_items[self.selected_index]
        item.update_appearance()
        self.update_code()

    def toggle_grid(self, checked):
        self.canvas.show_grid = checked
        self.canvas.update()

    def update_grid_opacity(self, value):
        self.canvas.grid_opacity = value / 100.0
        self.canvas.update()

    def toggle_preview_mode(self, checked):
        self.canvas.preview_mode = checked
        self.canvas.show_grid = not checked
        self.grid_toggle.setChecked(not checked)
        self.canvas.update()
        for item in self.canvas_items:
            item.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_selected()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
            self.duplicate_selected()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.undo()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Y:
            self.redo()
        super().keyPressEvent(event)

    def duplicate_selected(self):
        if self.selected_index < 0:
            return
        self.push_undo()
        src = self.assets[self.selected_index]
        new_asset = copy.deepcopy(src)
        new_asset["final_state"]["x"] += 0.5
        new_asset["final_state"]["y"] -= 0.5
        self.add_svg_asset_obj(new_asset)

    def add_svg_asset(self, file_path):
        asset = {
            "name": Path(file_path).name,
            "path": file_path.replace("\\", "/"),
            "initial_state": {
                "x": 0.0, "y": 0.0, "scale": 1.0, "rotation": 0, "opacity": 1.0,
                "svg": file_path.replace("\\", "/")
            },
            "final_state": {
                "x": 0.0, "y": 0.0, "scale": 1.0, "rotation": 0, "opacity": 1.0,
                "svg": file_path.replace("\\", "/")
            },
            "anim": "Path", "easing": "Smooth",
            "delay": 0.0, "duration": 2.0, "sequence_mode": False,
            "visible": True, "locked": False
        }
        self.add_svg_asset_obj(asset)

    def add_svg_asset_obj(self, asset):
        # Ensure visible/locked fields exist for older project files
        asset.setdefault("visible", True)
        asset.setdefault("locked", False)

        self.assets.append(asset)
        idx = len(self.assets) - 1
        item = DraggableSVGItem(asset, self, idx)
        self.canvas.scene().addItem(item)
        self.canvas_items.append(item)

        # Apply lock state
        if asset.get("locked", False):
            item.set_locked(True)

        # Custom Layer Widget
        list_item = QListWidgetItem(self.layer_list)
        list_item.setSizeHint(QSize(200, 72))
        list_item.setData(Qt.UserRole, id(asset))
        widget = LayerWidget(asset["name"], asset["path"], idx)
        widget.visibility_toggled.connect(self.on_asset_visibility_changed)
        widget.lock_toggled.connect(self.on_asset_lock_changed)
        self.layer_list.setItemWidget(list_item, widget)

        # Update timeline
        self.timeline_panel.set_assets(self.assets)

        self.update_code()

    def show_layer_context_menu(self, pos):
        item = self.layer_list.itemAt(pos)
        if not item:
            return
        self.selected_index = self.layer_list.row(item)

        menu = QMenu(self)
        menu.setStyleSheet(f"background: {COLOR_BG_LIGHT}; border: 1px solid {COLOR_BORDER};")
        dup_action = menu.addAction("Duplicate")
        del_action = menu.addAction("Delete")
        center_action = menu.addAction("Center on Stage")

        action = menu.exec(self.layer_list.mapToGlobal(pos))
        if action == dup_action:
            self.duplicate_selected()
        elif action == del_action:
            self.delete_selected()
        elif action == center_action:
            self.center_selected()

    def update_code(self):
        if hasattr(self, "initializing") and self.initializing:
            return
        if not hasattr(self, "code_view"):
            return

        ordered_assets = []
        try:
            for i in range(self.layer_list.count()):
                ordered_assets.append(self.assets[i])
        except (AttributeError, RuntimeError):
            return

        params = {"bg_color": self.bg_combo.currentText(), "fit_padding": 1.5}
        self.code_view.setPlainText(StudioCore.generate_scene_code(params, ordered_assets))

    def center_selected(self):
        if self.selected_index < 0:
            return
        self.push_undo()
        asset = self.assets[self.selected_index]
        asset["final_state"]["x"] = 0.0
        asset["final_state"]["y"] = 0.0
        asset["initial_state"]["x"] = 0.0
        asset["initial_state"]["y"] = 0.0
        self.canvas_items[self.selected_index].update_appearance()
        self.update_code()

    def distribute_selected(self):
        if not self.assets:
            return
        self.push_undo()
        count = len(self.assets)
        if count < 2:
            self.center_selected()
            return

        total_span = 8.0
        start_x = -total_span / 2
        step = total_span / (count - 1)

        for i, asset in enumerate(self.assets):
            asset["final_state"]["x"] = start_x + (i * step)
            asset["final_state"]["y"] = 0.0
            asset["initial_state"]["x"] = asset["final_state"]["x"]
            asset["initial_state"]["y"] = 0.0
            self.canvas_items[i].update_appearance()

        self.update_code()
        self.console.append(f">>> Distributed {count} assets horizontally.")

    def clear_canvas(self):
        self.push_undo()
        self.assets = []
        self.canvas_items = []
        self.selected_index = -1
        self.layer_list.clear()
        self.canvas.scene().clear()

        # Recreate Vignette as scene.clear() destroys it
        self.canvas.setup_vignette()

        self.timeline_panel.set_assets(self.assets)
        self.console.append(">>> Workspace Cleared.")
        self.update_code()

    def delete_selected(self):
        if self.selected_index >= 0:
            self.push_undo()
            self.layer_list.takeItem(self.selected_index)
            item = self.canvas_items.pop(self.selected_index)
            self.canvas.scene().removeItem(item)
            self.assets.pop(self.selected_index)
            self.selected_index = -1
            self.timeline_panel.set_assets(self.assets)
            self.update_code()

    def start_render(self):
        if not self.assets:
            return
        self.render_btn.setEnabled(False)
        self.console.clear()
        self.console.append(">>> KINETIC PATH RENDER START...")
        params = {"bg_color": self.bg_combo.currentText(), "fit_padding": 1.5}
        quality_key = self.quality_mapping[self.quality_combo.currentText()]
        self.thread = RenderThread(params, self.assets, quality_key)
        self.thread.log_signal.connect(self.console.append)
        self.thread.finished.connect(lambda s: self.on_render_finished(s))
        self.thread.start()

    def on_render_finished(self, success):
        self.render_btn.setEnabled(True)
        if success:
            self.console.append("\n>>> RENDER EXPORT SUCCESSFUL.")
        else:
            self.console.append("\n>>> RENDER FAILED.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SVGStudioWYSIWYG()
    window.show()
    sys.exit(app.exec())
