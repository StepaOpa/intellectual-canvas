import os
import math
from dataclasses import dataclass, field
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QSize, QRect
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QBrush
from PySide6.QtSvg import QSvgGenerator  # Добавлен импорт для SVG

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
        self.camera_opacity = 1.0
        
        self.cursor_pos: QPointF = QPointF(-1, -1)
        self.cursor_active: bool = False
        self.cursor_gesture: str = "idle"
        
        self.allow_drawing = True
        self.allow_erasing = True

        self.strokes: List[Stroke] = []
        self.undo_stack: List[Stroke] = []
        self.redo_stack: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None

        self.current_color = QColor("#3498DB")
        self.current_tool = "brush"
        self.brush_size = 12.0
        self.eraser_size = 60.0
        
        self.min_draw_distance = 4.0 

        self._image = QImage(width, height, QImage.Format.Format_ARGB32)
        self._image.fill(Qt.transparent)

    def set_camera_frame(self, image: QImage):
        self.camera_frame = image

    def set_camera_opacity(self, opacity: float):
        self.camera_opacity = max(0.0, min(1.0, opacity))

    def toggle_grid(self, show: bool):
        self.show_grid = show

    def update_cursor(self, x: float, y: float, gesture: str):
        self.cursor_pos = QPointF(x, y)
        self.cursor_gesture = gesture
        self.cursor_active = (x != -1 and y != -1)

    def set_tool(self, tool: str):
        self.current_tool = tool

    def set_color(self, color: QColor):
        self.current_color = color
        if self.current_stroke and self.current_stroke.tool == "brush":
            if self.current_stroke.points:
                last_pos = self.current_stroke.points[-1]
                self.end_stroke()
                self.begin_stroke(last_pos)

    def set_brush_size(self, size: float):
        self.brush_size = float(size)
        if self.current_stroke and self.current_stroke.tool == "brush":
            self.current_stroke.thickness = self.brush_size

    def set_eraser_size(self, size: float):
        self.eraser_size = float(size)
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
        if self.current_stroke and self.current_stroke.points:
            last_point = self.current_stroke.points[-1]
            
            dx = pos.x() - last_point.x()
            dy = pos.y() - last_point.y()
            dist = math.hypot(dx, dy)
            
            if dist < self.min_draw_distance:
                return

            self.current_stroke.points.append(pos)
            
            if len(self.current_stroke.points) >= 2:
                p1 = self.current_stroke.points[-2]
                p2 = self.current_stroke.points[-1]
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
        pen.setWidthF(stroke.thickness)
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
        
        painter.fillRect(target_rect, Qt.white)
        
        painter.translate(self.offset)
        painter.scale(self.scale_factor, self.scale_factor)
        
        if self.model.camera_frame and self.model.camera_opacity > 0.01:
            painter.save()
            painter.setOpacity(self.model.camera_opacity)
            painter.drawImage(QRectF(0, 0, self.model.width, self.model.height), self.model.camera_frame)
            painter.restore()
            
        if self.model.background_image:
            painter.drawImage(0, 0, self.model.background_image)
            
        painter.drawImage(0, 0, self.model.image)
        
        if self.model.cursor_active:
             painter.setOpacity(1.0)
             self._draw_cursor(painter)

        painter.restore()

    def _draw_cursor(self, painter: QPainter):
        x, y = self.model.cursor_pos.x(), self.model.cursor_pos.y()
        radius = self.model.current_thickness / 2
        
        if self.model.cursor_gesture == "erasing":
            pen = QPen(QColor(255, 50, 50), 3)
            brush = QBrush(QColor(255, 50, 50, 100))
        
        elif self.model.cursor_gesture == "drawing":
            pen = QPen(Qt.white, 2)
            brush = QBrush(self.model.current_color)
            
            painter.setPen(QPen(Qt.black, 4))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(x, y), radius, radius)
            
            color_with_alpha = QColor(self.model.current_color)
            color_with_alpha.setAlpha(150)
            brush = QBrush(color_with_alpha)
            
        else:
            pen = QPen(Qt.white, 3)
            brush = QBrush(Qt.transparent)
            radius = max(radius, 8)
            painter.setPen(QPen(Qt.black, 5))
            painter.drawEllipse(QPointF(x, y), radius, radius)

        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawEllipse(QPointF(x, y), radius, radius)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white if self.model.cursor_gesture != "erasing" else Qt.black)
        painter.drawEllipse(QPointF(x, y), 2, 2)

    def save_to_file(self, filename_hint: str = "artwork") -> bool:
        """Сохранение в растровый формат (PNG/JPG)"""
        result = QImage(self.model.width, self.model.height, QImage.Format_ARGB32)
        result.fill(Qt.white) 
        
        painter = QPainter(result)
        if self.model.background_image:
            painter.drawImage(0, 0, self.model.background_image)
            
        painter.drawImage(0, 0, self.model.image)
        painter.end()
        
        return result.save(filename_hint)

    def save_to_svg(self, filename: str) -> bool:
        """Сохранение в векторный формат SVG"""
        generator = QSvgGenerator()
        generator.setFileName(filename)
        generator.setSize(QSize(self.model.width, self.model.height))
        generator.setViewBox(QRect(0, 0, self.model.width, self.model.height))
        generator.setTitle("Smart Canvas Artwork")
        
        painter = QPainter()
        if not painter.begin(generator):
            return False
            
        # 1. Заливаем белым фоном
        painter.fillRect(QRect(0, 0, self.model.width, self.model.height), Qt.white)
        
        # 2. Если есть фоновая картинка, рисуем её
        if self.model.background_image:
            painter.drawImage(0, 0, self.model.background_image)
            
        # 3. Перерисовываем векторы
        # ВАЖНО: Мы не рисуем растр self.model.image, мы перерисовываем штрихи из истории
        for stroke in self.model.undo_stack:
            pen = QPen(stroke.color)
            
            # Для ластика в SVG используем белую кисть (перекрытие)
            if stroke.tool == "eraser":
                pen.setColor(Qt.white)
            
            pen.setWidthF(stroke.thickness)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            
            if len(stroke.points) > 1:
                painter.drawPolyline(stroke.points)
            elif len(stroke.points) == 1:
                # Точка
                painter.setBrush(pen.color())
                painter.setPen(Qt.NoPen)
                r = stroke.thickness / 2
                painter.drawEllipse(stroke.points[0], r, r)
        
        painter.end()
        return True