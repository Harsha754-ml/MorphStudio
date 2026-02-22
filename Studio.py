import sys
import json
import math
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
                             QSlider, QLabel, QComboBox, QTextEdit, QFileDialog, 
                             QProgressBar, QFrame, QSplitter, QGroupBox, QFormLayout,
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                             QGraphicsPixmapItem, QGraphicsItem, QCheckBox, QTabWidget,
                             QScrollArea, QToolButton, QSpinBox, QMenu, QGraphicsObject)
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QPointF, QSize, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QBrush, QPen, QPixmap, QDragEnterEvent, QDropEvent, QPainter, QLinearGradient, QAction
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtSvg import QSvgRenderer

from studio_core import StudioCore, PROJECT_ROOT

# --- PROFESSIONAL DESIGN SYSTEM ---
COLOR_BG_DARK = "#0e0f12"      
COLOR_BG_LIGHT = "#16171a"     
COLOR_PANEL = "#1c1e22"
COLOR_ACCENT = "#00d2ff"       
COLOR_ACCENT_DIM = "rgba(0, 210, 255, 0.12)"
COLOR_TEXT_PRIMARY = "#f5f5f7"
COLOR_TEXT_SECONDARY = "#8b949e"
COLOR_BORDER = "rgba(255, 255, 255, 0.05)"
COLOR_CANVAS = "#050507"

FONT_MAIN = "Inter"
FONT_MONO = "JetBrains Mono"

GRID_8 = 8  # Strict 8px spacing grid

MANIM_WIDTH = 14.22222222  
MANIM_HEIGHT = 8.0

class AnimatedButton(QPushButton):
    """A button with smooth hover scaling and depth effects."""
    def __init__(self, text, parent=None, is_accent=False):
        super().__init__(text, parent)
        self.is_accent = is_accent
        self._scale = 1.0
        
        self._anim = QPropertyAnimation(self, b"scale")
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setGraphicsEffect(None) # Removed heavy shadows

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
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Apply scaling from center
        painter.translate(self.width()/2, self.height()/2)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width()/2, -self.height()/2)
        
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
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())
        painter.end()

class LayerWidget(QWidget):
    def __init__(self, name, svg_path, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(48, 48)
        self.thumb.setStyleSheet(f"background: {COLOR_BG_DARK}; border-radius: 4px; border: 1px solid {COLOR_BORDER};")
        
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
        
        # Drag Handle (Visual only for now)
        handle = QLabel("⋮⋮")
        handle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 16px;")
        layout.addWidget(handle)

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
                padding: 8px; text-align: left; width: 1000px;
            }}
            QToolButton:checked {{ border-bottom: none; }}
        """)
        self.toggle_btn.clicked.connect(self.on_toggle)
        
        self.content = QWidget()
        self.content.setVisible(False)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 16, 16, 16) # Unified Internal Padding
        self.content_layout.setSpacing(12) # Consistent Vertical Rhythm
        
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
            manim_x = round((value.x() / 400.0) * (MANIM_WIDTH / 2.0), 2)
            manim_y = round((-value.y() / 225.0) * (MANIM_HEIGHT / 2.0), 2)
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
        super().paint(painter, option, widget)

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
            # We'll still setup a placeholder rect
            self._rect = QRectF(-50, -50, 100, 100)
        else:
            bounds = self.renderer.viewBox()
            aspect = bounds.width() / bounds.height() if bounds.height() != 0 else 1
            if aspect > 1:
                w, h = 100, 100 / aspect
            else:
                w, h = 100 * aspect, 100
            self._rect = QRectF(-w/2, -h/2, w, h)
        
        self.setFlags(QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemIsSelectable | 
                      QGraphicsItem.ItemIsFocusable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        
        self._pen = QPen(QColor(COLOR_BORDER), 1)
        self._brush = QBrush(QColor(40, 40, 45, 50))
        self.setCacheMode(QGraphicsItem.NoCache) # FIX: Disable caching
        
        self.handle = StartHandle(self)
        self.update_appearance()

    def boundingRect(self):
        # SIMPLIFIED: Static bounding box with generous padding to prevent 
        # recursion/crash during early init.
        return self._rect.adjusted(-50, -50, 50, 50)

    def update_pen(self):
        color = QColor(COLOR_ACCENT) if self.isSelected() else QColor(COLOR_BORDER)
        width = 2.5 if self.isSelected() else 1
        self._pen = QPen(color, width)
        self.update()

    def update_appearance(self):
        if self._block_recursion: return
        self._block_recursion = True
        try:
            # Final State is the base transform of the item
            final = self.asset["final_state"]
            self.setScale(final["scale"])
            self.setRotation(final["rotation"])
            
            px = (final["x"] / (MANIM_WIDTH / 2.0)) * 400.0
            py = (-final["y"] / (MANIM_HEIGHT / 2.0)) * 225.0
            self.setPos(px, py)
            
            # Initial State is the handle position (offset from item center)
            initial = self.asset["initial_state"]
            sx = (initial["x"] / (MANIM_WIDTH / 2.0)) * 400.0 - px
            sy = (-initial["y"] / (MANIM_HEIGHT / 2.0)) * 225.0 - py
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
            return t * t * (3 - 2 * t) # Smooth
        
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
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # 1. Context Analysis
        is_preview = self.app.canvas.preview_mode
        active_mode = self.app.get_active_inspector_section()
        is_selected = self.isSelected()
        
        # Mode Logic
        mode_motion = (active_mode == "MOTION") and is_selected and not is_preview
        mode_transform = (active_mode == "TRANSFORM") and is_selected and not is_preview
        
        # 2. Interpolated State for Main Body
        scrubber_t = self.app.timeline.value() / 1000.0
        state = self.get_interpolated_state(scrubber_t)
        
        # Manim Units -> Pixel Mapping
        tx = (state["x"] / (MANIM_WIDTH / 2.0)) * 400.0
        ty = (-state["y"] / (MANIM_HEIGHT / 2.0)) * 225.0
        
        # Base Position (the item's actual pos() in the scene)
        final = self.asset["final_state"]
        fx = (final["x"] / (MANIM_WIDTH / 2.0)) * 400.0
        fy = (-final["y"] / (MANIM_HEIGHT / 2.0)) * 225.0
        
        # Save Painter for Body
        painter.save()
        # Translate RELATIVE to the item's origin (pos())
        painter.translate(tx - fx, ty - fy)
        painter.rotate(state["rotation"])
        painter.scale(state["scale"], state["scale"])
        painter.setOpacity(state["opacity"])
        
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
            # We draw in scene coordinates or relative to 0,0 (final pos)
            # Path goes from initial to final
            init = self.asset["initial_state"]
            final = self.asset["final_state"]
            
            # Pixel coords
            isx = (init["x"] / (MANIM_WIDTH / 2.0)) * 400.0
            isy = (-init["y"] / (MANIM_HEIGHT / 2.0)) * 225.0
            fsx = (final["x"] / (MANIM_WIDTH / 2.0)) * 400.0
            fsy = (-final["y"] / (MANIM_HEIGHT / 2.0)) * 225.0
            
            # Path Logic (Dashed line with arrow)
            gradient = QLinearGradient(isx, isy, fsx, fsy)
            gradient.setColorAt(0, QColor(COLOR_ACCENT))
            gradient.setColorAt(1, QColor(COLOR_ACCENT, 50))
            
            pen = QPen(QBrush(gradient), 1.5, Qt.PenStyle.DashLine)
            pen.setDashOffset(self.app.animation_offset)
            painter.setPen(pen)
            painter.drawLine(QPointF(isx, isy), QPointF(fsx, fsy))
            
            # Arrowhead at Final
            angle = math.atan2(fsy - isy, fsx - isx)
            arrow_size = 10
            p1 = QPointF(fsx, fsy)
            p2 = QPointF(fsx - math.cos(angle - math.pi/6) * arrow_size, 
                         fsy - math.sin(angle - math.pi/6) * arrow_size)
            p3 = QPointF(fsx - math.cos(angle + math.pi/6) * arrow_size, 
                         fsy - math.sin(angle + math.pi/6) * arrow_size)
            painter.setBrush(QBrush(QColor(COLOR_ACCENT)))
            painter.drawPolygon([p1, p2, p3])
            painter.restore()
            
        # Ghosting (Only in Motion Mode & Not scrubbing)
        if mode_motion and self.app.timeline.value() == 0:
            for i in range(1, 6):
                t = i / 6.0
                g_state = self.get_interpolated_state(t)
                gx = (g_state["x"] / (MANIM_WIDTH / 2.0)) * 400.0
                gy = (-g_state["y"] / (MANIM_HEIGHT / 2.0)) * 225.0
                
                painter.save()
                painter.translate(gx, gy)
                painter.rotate(g_state["rotation"])
                painter.scale(g_state["scale"], g_state["scale"])
                painter.setOpacity(0.1 + (t * 0.15))
                self.renderer.render(painter, self._rect)
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
        
        # Lock Scene to Manim 16:9 Ratio
        self.scene().setSceneRect(-400, -225, 800, 450)
        
        # Viewport Architecture: Cinematic Mode
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Interaction
        self.setDragMode(QGraphicsView.NoDrag) # Cinematic focus
        self.setStyleSheet("background: transparent; border: none;")
        
        # Cinematic Controls
        self.show_grid = False
        self.grid_opacity = 0.02
        self.preview_mode = False
        
        self.mode_badge = ModeIndicator(self)
        
        self.setup_vignette()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_to_stage()

    def setup_vignette(self):
        # Vignette Overlay (Matches Stage exactly)
        self.vignette = QGraphicsRectItem(-400, -225, 800, 450)
        self.vignette.setZValue(1000)
        self.vignette.setFlag(QGraphicsItem.ItemHasNoContents, False)
        self.update_vignette()
        self.scene().addItem(self.vignette)

    def update_vignette(self):
        from PySide6.QtGui import QRadialGradient
        radial = QRadialGradient(0, 0, 500)
        radial.setColorAt(0, QColor(0, 0, 0, 0))
        radial.setColorAt(1, QColor(0, 0, 0, 80))
        self.vignette.setBrush(QBrush(radial))
        self.vignette.setPen(Qt.NoPen)
        self.vignette.setOpacity(0.4)

    def drawBackground(self, painter, rect):
        # Full viewport background match
        bg_color = QColor(self.app.bg_combo.currentText()) if hasattr(self, "app") else QColor(COLOR_CANVAS)
        painter.fillRect(rect, bg_color)
        
        if self.show_grid and not self.preview_mode:
            painter.setPen(QPen(QColor(255, 255, 255, int(self.grid_opacity * 255)), 0.5))
            grid_size = 50
            # Grid only within stage
            for x in range(-400, 401, grid_size):
                painter.drawLine(x, -225, x, 225)
            for y in range(-225, 226, grid_size):
                painter.drawLine(-400, y, 400, y)
        
        # Stage Frame (Ultra subtle neutral)
        if not self.preview_mode:
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            painter.drawRect(-400, -225, 800, 450)

    def drawForeground(self, painter, rect):
        # Cinematic Dimming outside Stage Area
        painter.save()
        from PySide6.QtGui import QRegion
        full_rect = rect.toRect()
        stage_rect = QRectF(-400, -225, 800, 450).toRect()
        
        dim_region = QRegion(full_rect) - QRegion(stage_rect)
        painter.setClipRegion(dim_region)
        painter.fillRect(rect, QColor(0, 0, 0, 160))
        painter.restore()

    def wheelEvent(self, event):
        # Disabled for strict viewport lock as per user request
        pass

    def fit_to_stage(self):
        # Ensure perfect 16:9 alignment with letterboxing
        self.fitInView(QRectF(-400, -225, 800, 450), Qt.KeepAspectRatio)
        if hasattr(self, "app"):
            scale_val = int(self.transform().m11() * 100)
            self.app.zoom_lbl.setText(f"{scale_val}%")
            # Sync timeline width to stage pixel width
            view_rect = self.mapFromScene(QRectF(-400, -225, 800, 450)).boundingRect()
            self.app.timeline_container.setFixedWidth(view_rect.width())

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

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
        self.setWindowTitle("SVG STUDIO PRO - KINETIC ORCHESTRATOR")
        self.resize(1500, 950)
        
        # 1. CORE STATE INITIALIZATION (Must happen before UI)
        self.assets = []
        self.canvas_items = [] 
        self.selected_index = -1
        self.initializing = True 
        self._block_recursion = False
        self.animation_offset = 0
        
        # 2. UI SETUP
        app_font = QFont(FONT_MAIN, 10)
        self.setFont(app_font)
        
        self.setup_ui()
        self.apply_styles()
        self.initializing = False
        
        # 3. PROFESSIONAL STARTUP ANIMATION (Simple Fade)
        self.setWindowOpacity(0.0)
        self._bloom = QPropertyAnimation(self, b"windowOpacity")
        self._bloom.setDuration(800)
        self._bloom.setStartValue(0.0)
        self._bloom.setEndValue(1.0)
        self._bloom.setEasingCurve(QEasingCurve.OutCubic)
        self._bloom.start()
        
        # Animation loop for path dash offset
        from PySide6.QtCore import QTimer
        self.dash_timer = QTimer(self)
        self.dash_timer.timeout.connect(self.animate_path)
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
        self.top_layout.setContentsMargins(GRID_8*2, GRID_8*2, GRID_8*2, GRID_8*2)
        self.top_layout.setSpacing(GRID_8*2)
        
        # --- 1. BRANDING BAR ---
        self.brand_bar = QFrame()
        self.brand_bar.setFixedHeight(50)
        self.brand_layout = QHBoxLayout(self.brand_bar)
        self.brand_layout.setContentsMargins(GRID_8, 0, GRID_8, 0)
        self.brand_layout.setSpacing(GRID_8*1.5)
        
        # Modern Morphing Symbol (Icon)
        self.brand_icon = QLabel("◈") # Modern glyph
        self.brand_icon.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 24px; font-weight: bold;")
        
        # Text Stack
        self.brand_text_container = QWidget()
        self.brand_text_vbox = QVBoxLayout(self.brand_text_container)
        self.brand_text_vbox.setContentsMargins(0, 0, 0, 0)
        self.brand_text_vbox.setSpacing(0)
        
        self.brand_title = QLabel("MorphStudio")
        self.brand_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 18px; font-weight: 600; letter-spacing: 0.5px;")
        
        self.brand_subtitle = QLabel("Vector Motion Engine")
        self.brand_subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px; font-weight: 300; text-transform: uppercase; letter-spacing: 1.5px;")
        
        self.brand_text_vbox.addWidget(self.brand_title)
        self.brand_text_vbox.addWidget(self.brand_subtitle)
        
        self.brand_layout.addWidget(self.brand_icon)
        self.brand_layout.addWidget(self.brand_text_container)
        self.brand_layout.addStretch()
        
        self.top_layout.addWidget(self.brand_bar)
        
        # Main Work Area
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(GRID_8*2)
        self.top_layout.addLayout(self.main_layout)
        
        # --- LEFT SIDEBAR (Layers) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(280)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(GRID_8*2, GRID_8*2, GRID_8*2, GRID_8*2)
        self.sidebar_layout.setSpacing(GRID_8*1.5)
        
        # Section Title: LAYERS
        self.layer_header = QLabel("LAYERS")
        self.layer_header.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 10px; letter-spacing: 1px;")
        self.sidebar_layout.addWidget(self.layer_header)
        
        self.sidebar_divider = QFrame()
        self.sidebar_divider.setFixedHeight(1)
        self.sidebar_divider.setStyleSheet(f"background: {COLOR_BORDER};")
        self.sidebar_layout.addWidget(self.sidebar_divider)
        
        # lbl_layers = QLabel("LAYERS") # This label is removed as per the new structure
        # lbl_layers.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        # self.sidebar_layout.addWidget(lbl_layers) # This widget is removed
        
        self.layer_list = QListWidget()
        self.layer_list.itemClicked.connect(self.select_by_index)
        self.layer_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layer_list.customContextMenuRequested.connect(self.show_layer_context_menu)
        self.sidebar_layout.addWidget(self.layer_list)
        
        self.add_btn = AnimatedButton("IMPORT SVG")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.clicked.connect(self.import_dialog)
        self.sidebar_layout.addWidget(self.add_btn)
        
        self.clear_btn = AnimatedButton("CLEAR ALL")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.setObjectName("DeleteButton") # Style still handled by CSS for text color
        self.clear_btn.clicked.connect(self.clear_canvas)
        self.sidebar_layout.addWidget(self.clear_btn)
        
        self.sidebar_layout.addStretch()
        
        # Left Sidebar Shadow
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
        center_layout.setSpacing(GRID_8*2)
        
        # --- STAGE CONTAINER (Upgraded) ---
        self.stage_box = QFrame()
        self.stage_box.setObjectName("StageBox")
        self.sb_layout = QVBoxLayout(self.stage_box)
        self.sb_layout.setContentsMargins(GRID_8*2, GRID_8*2, GRID_8*2, GRID_8*2)
        
        # Preview Overlay
        self.preview_overlay = QLabel("MorphStudio Preview")
        self.preview_overlay.setAlignment(Qt.AlignCenter)
        self.preview_overlay.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-size: 10px; font-weight: 300; letter-spacing: 2px; text-transform: uppercase;")
        self.sb_layout.addWidget(self.preview_overlay)
        
        self.canvas = StudioCanvas()
        self.canvas.app = self # Link for coordination
        self.canvas.file_dropped.connect(self.add_svg_asset)
        self.canvas.scene().selectionChanged.connect(self.on_selection_changed)
        self.sb_layout.addWidget(self.canvas, alignment=Qt.AlignCenter)
        
        center_layout.addStretch(1)
        center_layout.addWidget(self.stage_box, alignment=Qt.AlignCenter)
        
        # --- TIMELINE AREA ---
        self.timeline_wrapper = QWidget()
        self.tw_layout = QVBoxLayout(self.timeline_wrapper)
        self.tw_layout.setContentsMargins(0, 0, 0, 0)
        self.tw_layout.setSpacing(GRID_8)
        
        self.timeline_container = QFrame()
        self.timeline_container.setObjectName("TimelineContainer")
        self.tc_layout = QHBoxLayout(self.timeline_container)
        self.tc_layout.setContentsMargins(GRID_8*2, 0, GRID_8*2, 0)
        self.tc_layout.setSpacing(GRID_8*1.5)
        
        lbl_0 = QLabel("0%")
        lbl_0.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px; font-weight: bold;")
        self.tc_layout.addWidget(lbl_0)
        
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setObjectName("PreviewSlider")
        self.timeline.setRange(0, 1000)
        self.timeline.setValue(0)
        self.timeline.valueChanged.connect(self.on_timeline_changed)
        self.tc_layout.addWidget(self.timeline)
        
        lbl_100 = QLabel("100%")
        lbl_100.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px; font-weight: bold;")
        self.tc_layout.addWidget(lbl_100)
        
        self.tw_layout.addWidget(self.timeline_container, alignment=Qt.AlignCenter)
        center_layout.addWidget(self.timeline_wrapper)
        
        # Add Canvas Tools above the console
        self.toolbar_container = QWidget()
        tb_layout = QHBoxLayout(self.toolbar_container)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left-aligned toolbar
        t_bar = QFrame()
        t_bar.setStyleSheet(f"background: {COLOR_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 16px;")
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
        self.zoom_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
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
        
        # Inspector Header
        self.insp_header = QLabel("PROPERTIES")
        self.insp_header.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 10px; letter-spacing: 1px; padding: {GRID_8*2}px;")
        self.insp_layout.addWidget(self.insp_header)
        
        self.insp_divider = QFrame()
        self.insp_divider.setFixedHeight(1)
        self.insp_divider.setStyleSheet(f"background: {COLOR_BORDER};")
        self.insp_layout.addWidget(self.insp_divider)
        
        # Inspector Scroll Area
        self.insp_scroll = QScrollArea()
        self.insp_scroll.setWidgetResizable(True)
        self.insp_scroll.setFrameShape(QFrame.NoFrame)
        self.insp_content = QWidget()
        self.inspector_layout = QVBoxLayout(self.insp_content)
        self.inspector_layout.setContentsMargins(GRID_8*2, GRID_8*2, GRID_8*2, GRID_8*2)
        self.inspector_layout.setSpacing(GRID_8*2)
        self.insp_scroll.setWidget(self.insp_content)
        self.insp_layout.addWidget(self.insp_scroll)
        
        # Section 1: TRANSFORM
        self.trans_section = CollapsibleSection("TRANSFORM")
        self.trans_section.app_parent = self
        self.trans_form = QFormLayout()
        self.trans_form.setSpacing(12)
        self.scale_slider = self.create_slider("Scale", 10, 500, 100, self.trans_form)
        self.rot_slider = self.create_slider("Rotation", -360, 360, 0, self.trans_form)
        
        # Smart Tools
        tool_group = QGroupBox("SMART TOOLS")
        tool_layout = QHBoxLayout(tool_group)
        btn_center = QPushButton("🎯 CENTER")
        btn_center.setMinimumHeight(28)
        btn_center.clicked.connect(self.center_selected)
        tool_layout.addWidget(btn_center)
        self.trans_form.addRow(tool_group) # Add smart tools to transform section
        
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
        self.inspector_layout.addStretch() # Push everything up
        
        self.main_layout.addWidget(self.inspector_panel)

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
        spin.setStyleSheet(f"background: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 2px;")
        
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
                border-right: 1px solid {COLOR_BORDER}; 
            }}
            #Inspector {{ border-right: none; border-left: 1px solid {COLOR_BORDER}; }}
            
            #StageBox {{ 
                background: {COLOR_BG_DARK}; 
                border: 1px solid {COLOR_BORDER}; 
                border-radius: 8px; 
            }}
            
            #TimelineContainer {{
                background: {COLOR_PANEL};
                border: 1px solid {COLOR_BORDER};
                border-radius: 20px;
                height: 40px;
            }}
            
            QGroupBox {{ font-weight: 600; font-size: 10px; color: {COLOR_TEXT_SECONDARY}; 
                         border: none; margin-top: {GRID_8*2}px; padding-top: {GRID_8}px; }}
            
            QPushButton {{ 
                background-color: {COLOR_BG_LIGHT}; 
                border: 1px solid {COLOR_BORDER}; 
                border-radius: 4px; 
                padding: {GRID_8}px {GRID_8*2}px; 
                font-weight: 600; 
                color: {COLOR_TEXT_PRIMARY}; 
            }}
            QPushButton:hover {{ 
                background-color: {COLOR_PANEL}; 
                border-color: {COLOR_ACCENT}; 
            }}
            
            #RenderButton {{ 
                background: {COLOR_ACCENT}; 
                color: {COLOR_BG_DARK}; 
                border: none; 
                padding: {GRID_8*1.5}px;
                font-size: 12px;
                letter-spacing: 0.5px;
            }}
            #RenderButton:hover {{ background: #ffffff; }}
            
            QListWidget {{ background: transparent; border: none; }}
            QListWidget::item {{ 
                padding: {GRID_8}px; 
                border-radius: 4px; 
                margin-bottom: 2px;
                color: {COLOR_TEXT_SECONDARY};
            }}
            QListWidget::item:hover {{ background: rgba(255, 255, 255, 0.03); }}
            QListWidget::item:selected {{ background: {COLOR_ACCENT_DIM}; color: {COLOR_ACCENT}; font-weight: 600; }}
            
            QComboBox {{ background: {COLOR_BG_LIGHT}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 4px {GRID_8}px; }}
            
            QSlider::groove:horizontal {{ height: 2px; background: {COLOR_BORDER}; }}
            QSlider::handle:horizontal {{ background: {COLOR_ACCENT}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}
            
            #PreviewSlider::groove:horizontal {{ height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; }}
            #PreviewSlider::handle:horizontal {{ background: #ffffff; width: 4px; height: 16px; margin: -6px 0; border-radius: 2px; }}
            
            QScrollBar:vertical {{ border: none; background: transparent; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {COLOR_BORDER}; border-radius: 2px; }}
            
            QTextEdit {{ background: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; color: {COLOR_TEXT_SECONDARY}; padding: {GRID_8}px; }}
            
            QTabWidget::pane {{ border-top: 1px solid {COLOR_BORDER}; background: {COLOR_PANEL}; }}
            QTabBar::tab {{ background: transparent; padding: {GRID_8}px {GRID_8*2}px; color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 10px; }}
            QTabBar::tab:selected {{ color: {COLOR_ACCENT}; border-bottom: 2px solid {COLOR_ACCENT}; }}
        """)

    def import_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Import SVGs", "", "SVG Files (*.svg)")
        for f in files: self.add_svg_asset(f)

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
        if self._block_recursion: return
        self._block_recursion = True 
        
        # Calculate Current Manim Position for the drop point
        new_manim_x = round((pos.x() / 400.0) * (MANIM_WIDTH / 2.0), 2)
        new_manim_y = round((-pos.y() / 225.0) * (MANIM_HEIGHT / 2.0), 2)
        
        try:
            idx = self.canvas_items.index(item)
            asset = self.assets[idx]
            
            # 1. Calculate the Delta (How far did the user drag?)
            old_final = asset["final_state"]
            dx = new_manim_x - old_final["x"]
            dy = new_manim_y - old_final["y"]
            
            # 2. Update BOTH states by the same delta (Moves entire animation path)
            asset["initial_state"]["x"] += dx
            asset["initial_state"]["y"] += dy
            asset["final_state"]["x"] = new_manim_x
            asset["final_state"]["y"] = new_manim_y
            
            self.update_code()
            
            # 3. Synchronize Handle visual position relative to the item
            initial = asset["initial_state"]
            hx = (initial["x"] / (MANIM_WIDTH / 2.0)) * 400.0 - pos.x()
            hy = (-initial["y"] / (MANIM_HEIGHT / 2.0)) * 225.0 - pos.y()
            item.handle.setPos(hx, hy)
            
            # 4. Trigger localized updates
            item.update()
            
        except (ValueError, KeyError): pass
        finally:
            self._block_recursion = False

    def update_ui_from_asset(self):
        if self.selected_index < 0: return
        asset = self.assets[self.selected_index]
        initial = asset["initial_state"]
        final = asset["final_state"]
        
        self.scale_slider.blockSignals(True)
        self.rot_slider.blockSignals(True)
        self.delay_slider.blockSignals(True)
        self.dur_slider.blockSignals(True)
        
        # We sync UI directly to FINAL state for Transform, but handles manage INITIAL
        self.scale_slider.setValue(int(final["scale"] * 100))
        self.rot_slider.setValue(final["rotation"])
        
        self.delay_slider.setValue(int(asset["delay"] * 100))
        self.dur_slider.setValue(int(asset["duration"] * 100))
        self.anim_combo.setCurrentText(asset["anim"])
        self.easing_combo.setCurrentText(asset["easing"])
        self.seq_check.setChecked(asset["sequence_mode"])
        
        self.scale_slider.blockSignals(False)
        self.rot_slider.blockSignals(False)
        self.delay_slider.blockSignals(False)
        self.dur_slider.blockSignals(False)

    def get_active_inspector_section(self):
        # Determine mode based on expanded sections
        if self.motion_section.content.isVisible(): return "MOTION"
        if self.trans_section.content.isVisible(): return "TRANSFORM"
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
        if self.selected_index < 0: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Morph Target", "", "SVG Files (*.svg)")
        if file_path:
            self.assets[self.selected_index]["final_state"]["svg"] = file_path.replace("\\", "/")
            self.update_code()
            # We could load second renderer here if preview needed
            self.canvas_items[self.selected_index].update()

    def on_timeline_changed(self, value):
        t = value / 1000.0
        # Debug Log
        # print(f"PREVIEW | Slider: {value} | Normalized t: {t:.3f}")
        
        # Trigger redraw for all items to see full scene orchestration
        for item in self.canvas_items:
            item.update()

    def sync_asset_to_ui(self):
        if self.selected_index < 0: return
        asset = self.assets[self.selected_index]
        asset["final_state"]["scale"] = self.scale_slider.value() / 100.0
        asset["final_state"]["rotation"] = self.rot_slider.value()
        asset["delay"] = self.delay_slider.value() / 100.0
        asset["duration"] = self.dur_slider.value() / 100.0
        asset["anim"] = self.anim_combo.currentText()
        asset["easing"] = self.easing_combo.currentText()
        asset["sequence_mode"] = self.seq_check.isChecked()
        
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
        super().keyPressEvent(event)

    def duplicate_selected(self):
        if self.selected_index < 0: return
        src = self.assets[self.selected_index]
        import copy
        new_asset = copy.deepcopy(src)
        new_asset["final_state"]["x"] += 0.5
        new_asset["final_state"]["y"] -= 0.5
        self.add_svg_asset_obj(new_asset)

    def add_svg_asset(self, file_path):
        asset = {
            "name": Path(file_path).name, "path": file_path.replace("\\", "/"),
            "initial_state": {
                "x": -3.0, "y": 0.0, "scale": 1.0, "rotation": 0, "opacity": 1.0, "svg": file_path.replace("\\", "/")
            },
            "final_state": {
                "x": 0.0, "y": 0.0, "scale": 1.0, "rotation": 0, "opacity": 1.0, "svg": file_path.replace("\\", "/")
            },
            "anim": "Path", "easing": "Smooth",
            "delay": 0.0, "duration": 2.0, "sequence_mode": False
        }
        self.add_svg_asset_obj(asset)

    def add_svg_asset_obj(self, asset):
        self.assets.append(asset)
        idx = len(self.assets) - 1
        item = DraggableSVGItem(asset, self, idx)
        self.canvas.scene().addItem(item)
        self.canvas_items.append(item)
        
        # Custom Layer Widget
        list_item = QListWidgetItem(self.layer_list)
        list_item.setSizeHint(QSize(200, 72)) # Accommodate 48px thumb + padding
        widget = LayerWidget(asset["name"], asset["path"])
        self.layer_list.setItemWidget(list_item, widget)
        
        self.update_code()

    def show_layer_context_menu(self, pos):
        item = self.layer_list.itemAt(pos)
        if not item: return
        self.selected_index = self.layer_list.row(item)
        
        menu = QMenu(self)
        menu.setStyleSheet(f"background: {COLOR_BG_LIGHT}; border: 1px solid {COLOR_BORDER};")
        dup_action = menu.addAction("Duplicate")
        del_action = menu.addAction("Delete")
        center_action = menu.addAction("Center on Stage")
        
        action = menu.exec(self.layer_list.mapToGlobal(pos))
        if action == dup_action: self.duplicate_selected()
        elif action == del_action: self.delete_selected()
        elif action == center_action: self.center_selected()

    def update_code(self):
        if hasattr(self, "initializing") and self.initializing: return
        if not hasattr(self, "code_view"): return
        
        # Sync assets with list order
        ordered_assets = []
        try:
            for i in range(self.layer_list.count()):
                ordered_assets.append(self.assets[i])
        except (AttributeError, RuntimeError): 
            # Catch widget deletion or early access
            return
            
        params = {"bg_color": self.bg_combo.currentText(), "fit_padding": 1.5}
        self.code_view.setPlainText(StudioCore.generate_scene_code(params, ordered_assets))

    def center_selected(self):
        if self.selected_index < 0: return
        asset = self.assets[self.selected_index]
        asset["final_state"]["x"] = 0.0
        asset["final_state"]["y"] = 0.0
        self.canvas_items[self.selected_index].update_appearance()
        self.update_code()

    def clear_canvas(self):
        self.assets = []
        self.canvas_items = []
        self.selected_index = -1
        self.layer_list.clear()
        self.canvas.scene().clear()
        
        # Recreate Vignette as scene.clear() destroys it
        self.canvas.setup_vignette()
        
        self.console.append(">>> Workspace Cleared.")
        self.update_code()

    def delete_selected(self):
        if self.selected_index >= 0:
            self.layer_list.takeItem(self.selected_index)
            item = self.canvas_items.pop(self.selected_index)
            self.canvas.scene().removeItem(item)
            self.assets.pop(self.selected_index)
            self.selected_index = -1
            self.update_code()

    def start_render(self):
        if not self.assets: return
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
        if success: self.console.append("\n>>> RENDER EXPORT SUCCESSFUL.")
        else: self.console.append("\n>>> RENDER FAILED.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SVGStudioWYSIWYG()
    window.show()
    sys.exit(app.exec())
