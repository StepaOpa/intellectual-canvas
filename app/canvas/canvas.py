from dataclasses import dataclass, field
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen

@dataclass
class Stroke:
    points: List[QPointF] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor(0, 0, 0))
    thickness: float = 3.0
    tool: str = "brush"

class CanvasModel:
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        
        self.background_color: Optional[QColor] = None 
        self.background_image: Optional[QImage] = None
        self.camera_frame: Optional[QImage] = None
        
        self.grid_step = 80
        self.show_grid = True
        
        # Флаги разрешения жестов
        self.allow_drawing = True
        self.allow_erasing = True

        self.strokes: List[Stroke] = []
        self.undo_stack: List[Stroke] = []
        self.redo_stack: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None

        # Настройки
        self.current_color = QColor("#3498DB")
        self.current_tool = "brush"
        
        # Настройки инструментов
        self.brush_size = 12.0
        self.eraser_size = 60.0

        self._image = QImage(width, height, QImage.Format.Format_ARGB32)
        self._image.fill(Qt.transparent)

    def set_camera_frame(self, image: QImage):
        self.camera_frame = image

    def set_tool(self, tool: str):
        self.current_tool = tool

    def set_color(self, color: QColor):
        self.current_color = color
        # Если мы прямо сейчас рисуем, можно было бы менять и цвет, 
        # но обычно в граф. редакторах цвет штриха не меняется на лету.

    # --- ЛОГИКА МГНОВЕННОГО ПРИМЕНЕНИЯ РАЗМЕРА ---
    def set_brush_size(self, size: float):
        self.brush_size = float(size)
        # Если прямо сейчас рисуем КИСТЬЮ, обновляем толщину текущего штриха
        if self.current_stroke and self.current_stroke.tool == "brush":
            self.current_stroke.thickness = self.brush_size

    def set_eraser_size(self, size: float):
        self.eraser_size = float(size)
        # Если прямо сейчас стираем, обновляем толщину
        if self.current_stroke and self.current_stroke.tool == "eraser":
            self.current_stroke.thickness = self.eraser_size

    @property
    def current_thickness(self) -> float:
        if self.current_tool == "brush":
            return self.brush_size
        elif self.current_tool == "eraser":
            return self.eraser_size
        return 5.0

    def begin_stroke(self, pos: QPointF):
        self.current_stroke = Stroke(
            color=self.current_color if self.current_tool == "brush" else Qt.transparent,
            thickness=self.current_thickness,
            tool=self.current_tool
        )
        self.current_stroke.points.append(pos)
        self.redo_stack.clear()
        self._draw_point_to_buffer(pos)

    def continue_stroke(self, pos: QPointF):
        if self.current_stroke:
            self.current_stroke.points.append(pos)
            if len(self.current_stroke.points) >= 2:
                p1 = self.current_stroke.points[-2]
                p2 = self.current_stroke.points[-1]
                # Передаем stroke целиком, там уже обновленная толщина
                self._draw_segment_to_buffer(p1, p2, self.current_stroke)

    def end_stroke(self):
        if self.current_stroke and len(self.current_stroke.points) > 0:
            self.strokes.append(self.current_stroke)
            self.undo_stack.append(self.current_stroke)
        self.current_stroke = None

    def undo(self):
        if self.undo_stack:
            stroke = self.undo_stack.pop()
            self.redo_stack.append(stroke)
            self._rebuild_image()

    def redo(self):
        if self.redo_stack:
            stroke = self.redo_stack.pop()
            self.undo_stack.append(stroke)
            self._rebuild_image()

    def clear(self):
        self.strokes.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.background_image = None
        self._rebuild_image()

    def load_background(self, path: str):
        img = QImage(path)
        if not img.isNull():
            self.background_image = img.scaled(self.width, self.height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._rebuild_image()

    def _draw_point_to_buffer(self, point: QPointF):
        painter = QPainter(self._image)
        self._configure_painter(painter)
        if self.current_tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.current_stroke.color)
            r = self.current_stroke.thickness / 2
            painter.drawEllipse(point, r, r)
        painter.end()

    def _draw_segment_to_buffer(self, p1: QPointF, p2: QPointF, stroke: Stroke):
        painter = QPainter(self._image)
        self._configure_painter(painter)
        if stroke.tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        pen = QPen(stroke.color)
        pen.setWidthF(stroke.thickness) # Тут используется актуальная толщина
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()

    def _rebuild_image(self):
        self._image.fill(Qt.transparent)
        painter = QPainter(self._image)
        self._configure_painter(painter)
        for stroke in self.undo_stack:
            if stroke.tool == "eraser":
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
            else:
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(stroke.color)
            pen.setWidthF(stroke.thickness)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            if len(stroke.points) > 1:
                painter.drawPolyline(stroke.points)
            elif len(stroke.points) == 1:
                 painter.setPen(Qt.NoPen)
                 painter.setBrush(stroke.color)
                 r = stroke.thickness / 2
                 painter.drawEllipse(stroke.points[0], r, r)
        painter.end()

    def _configure_painter(self, painter: QPainter):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

    @property
    def image(self) -> QImage:
        return self._image


class RenderEngine:
    def __init__(self, model: CanvasModel):
        self.model = model
        self.scale_factor = 1.0
        self.offset = QPointF(0, 0)
        
    def zoom(self, delta_scale: float, mouse_pos: QPointF):
        old_scale = self.scale_factor
        new_scale = old_scale * delta_scale
        if new_scale < 0.1: new_scale = 0.1
        if new_scale > 5.0: new_scale = 5.0
        if new_scale == old_scale: return
        world_pos = (mouse_pos - self.offset) / old_scale
        new_offset = mouse_pos - (world_pos * new_scale)
        self.scale_factor = new_scale
        self.offset = new_offset

    def render_to_painter(self, painter: QPainter, target_rect: QRectF):
        painter.save()
        bg_color = self.model.background_color or QColor("#F3F5F7")
        painter.fillRect(target_rect, bg_color)
        painter.translate(self.offset)
        painter.scale(self.scale_factor, self.scale_factor)
        if self.model.camera_frame:
            painter.drawImage(QRectF(0, 0, self.model.width, self.model.height), self.model.camera_frame)
        if self.model.background_image:
            painter.drawImage(0, 0, self.model.background_image)
        painter.drawImage(0, 0, self.model.image)
        painter.restore()

    def save_to_file(self, path: str) -> bool:
        result = QImage(self.model.width, self.model.height, QImage.Format_ARGB32)
        result.fill(Qt.white)
        painter = QPainter(result)
        if self.model.background_image:
            painter.drawImage(0, 0, self.model.background_image)
        painter.drawImage(0, 0, self.model.image)
        painter.end()
        return result.save(path)