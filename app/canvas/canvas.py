from dataclasses import dataclass, field
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen

@dataclass
class Stroke:
    """Векторное представление штриха"""
    points: List[QPointF] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor(0, 0, 0))
    thickness: float = 3.0
    tool: str = "brush"

class CanvasModel:
    """Модель данных"""
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        
        # Слои фона
        self.background_color: Optional[QColor] = None 
        self.background_image: Optional[QImage] = None
        self.camera_frame: Optional[QImage] = None # <-- Новый слот для кадра
        
        # Настройки сетки
        self.grid_step = 80
        self.show_grid = True

        # История штрихов
        self.strokes: List[Stroke] = []
        self.undo_stack: List[Stroke] = []
        self.redo_stack: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None

        # Инструменты
        self.current_color = QColor("#3498DB")
        self.current_tool = "brush"
        self.brush_thickness = 12.0
        self.eraser_thickness = 60.0
        self.current_thickness = self.brush_thickness

        # Буфер рисования (только штрихи)
        self._image = QImage(width, height, QImage.Format.Format_ARGB32)
        self._image.fill(Qt.transparent)

    def set_camera_frame(self, image: QImage):
        """Обновление текущего кадра с камеры"""
        self.camera_frame = image

    def set_tool(self, tool: str):
        self.current_tool = tool
        if tool == "brush":
            self.current_thickness = self.brush_thickness
        elif tool == "eraser":
            self.current_thickness = self.eraser_thickness

    def set_color(self, color: QColor):
        self.current_color = color

    def set_thickness(self, thickness: float):
        self.current_thickness = float(thickness)
        if self.current_tool == "brush":
            self.brush_thickness = self.current_thickness
        elif self.current_tool == "eraser":
            self.eraser_thickness = self.current_thickness

    def begin_stroke(self, pos: QPointF):
        self.current_stroke = Stroke(
            color=self.current_color if self.current_tool == "brush" else Qt.transparent,
            thickness=self.current_thickness,
            tool=self.current_tool
        )
        self.current_stroke.points.append(pos)
        self.redo_stack.clear()

    def continue_stroke(self, pos: QPointF):
        if self.current_stroke:
            self.current_stroke.points.append(pos)
            self._draw_current_stroke_to_buffer()

    def end_stroke(self):
        if self.current_stroke and len(self.current_stroke.points) > 1:
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

    def _draw_current_stroke_to_buffer(self):
        if not self.current_stroke or len(self.current_stroke.points) < 2: return
        painter = QPainter(self._image)
        self._configure_painter(painter)
        self._draw_stroke_on_painter(painter, self.current_stroke)
        painter.end()

    def _rebuild_image(self):
        self._image.fill(Qt.transparent)
        painter = QPainter(self._image)
        self._configure_painter(painter)
        for stroke in self.undo_stack:
            self._draw_stroke_on_painter(painter, stroke)
        painter.end()

    def _configure_painter(self, painter: QPainter):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

    def _draw_stroke_on_painter(self, painter: QPainter, stroke: Stroke):
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
            for i in range(len(stroke.points) - 1):
                painter.drawLine(stroke.points[i], stroke.points[i+1])

    @property
    def image(self) -> QImage:
        return self._image


class RenderEngine:
    """Движок отображения"""
    def __init__(self, model: CanvasModel):
        self.model = model
        self.scale_factor = 1.0
        self.offset = QPointF(0, 0)

    def render_to_painter(self, painter: QPainter, target_rect: QRectF):
        painter.save()
        
        # 1. Заливка базовым цветом (чтобы PNG прозрачность фона работала корректно)
        bg_color = self.model.background_color or QColor("#F3F5F7")
        painter.fillRect(target_rect, bg_color)
        
        # 2. Трансформация камеры (Зум/Пан)
        painter.translate(self.offset)
        painter.scale(self.scale_factor, self.scale_factor)
        
        # 3. ОТРИСОВКА КАМЕРЫ (Полупрозрачно)
        if self.model.camera_frame:
            painter.save()
            painter.setOpacity(0.4)  # 40% непрозрачности (полупрозрачная)
            # Растягиваем камеру на весь текущий размер холста (или вписываем)
            # Сейчас предполагаем, что холст равен размеру камеры
            painter.drawImage(QRectF(0, 0, self.model.width, self.model.height), self.model.camera_frame)
            painter.restore()

        # 4. Статичная картинка-фон (если загружена через Open)
        if self.model.background_image:
            painter.drawImage(0, 0, self.model.background_image)

        # 5. Сетка (Если мы хотим чтобы она была ПОД штрихами, но НАД камерой)
        # В ui.py сетка рисуется поверх всего, но можно перенести сюда, если нужно
        
        # 6. Основной буфер штрихов
        painter.drawImage(0, 0, self.model.image)
        
        painter.restore()

    def save_to_file(self, path: str) -> bool:
        # При сохранении камеру обычно не сохраняют, только рисунок
        result = QImage(self.model.width, self.model.height, QImage.Format_ARGB32)
        result.fill(Qt.white) # Белый фон для сохранения
        
        painter = QPainter(result)
        if self.model.background_image:
            painter.drawImage(0, 0, self.model.background_image)
        painter.drawImage(0, 0, self.model.image)
        painter.end()
        return result.save(path)

    def screen_to_canvas(self, screen_pos: QPointF) -> QPointF:
        return (screen_pos - self.offset) / self.scale_factor