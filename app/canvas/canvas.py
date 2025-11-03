from dataclasses import dataclass, field
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen


@dataclass
class Stroke:
    """Класс для представления одного штриха на холсте"""
    points: List[QPointF] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor(0, 0, 0))
    thickness: float = 3.0
    tool: str = "brush"


class CanvasModel:
    """Модель холста для хранения данных и состояния рисования"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.background_color = QColor(255, 255, 255)
        
        # История штрихов
        self.strokes: List[Stroke] = []
        self.undo_stack: List[Stroke] = []
        self.redo_stack: List[Stroke] = []
        
        # Текущий активный штрих
        self.current_stroke: Optional[Stroke] = None
        
        # Настройки по умолчанию
        self.current_color = QColor(0, 0, 0)
        self.current_thickness = 3.0
        self.current_tool = "brush"
        
        # Изображение холста
        self._image = QImage(width, height, QImage.Format.Format_ARGB32)
        self._image.fill(self.background_color)
    
    def begin_stroke(self, pos: QPointF, tool: str = None):
        """Начало нового штриха"""
        if tool is None:
            tool = self.current_tool
            
        self.current_stroke = Stroke(
            color=self.current_color if tool == "brush" else self.background_color,
            thickness=self.current_thickness,
            tool=tool
        )
        self.current_stroke.points.append(pos)
        self.redo_stack.clear()
    
    def continue_stroke(self, pos: QPointF):
        """Продолжение текущего штриха"""
        if self.current_stroke:
            self.current_stroke.points.append(pos)
    
    def end_stroke(self):
        """Завершение текущего штриха"""
        if self.current_stroke and len(self.current_stroke.points) > 1:
            self.strokes.append(self.current_stroke)
            self.undo_stack.append(self.current_stroke)
        self.current_stroke = None
    
    def undo(self):
        """Отмена последнего действия"""
        if self.undo_stack:
            stroke = self.undo_stack.pop()
            self.redo_stack.append(stroke)
            self._rebuild_image()
    
    def redo(self):
        """Повтор отмененного действия"""
        if self.redo_stack:
            stroke = self.redo_stack.pop()
            self.undo_stack.append(stroke)
            self._rebuild_image()
    
    def clear(self):
        """Очистка холста"""
        self.strokes.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_stroke = None
        self._image.fill(self.background_color)
    
    def set_color(self, color: QColor):
        """Установка текущего цвета"""
        self.current_color = color
    
    def set_thickness(self, thickness: float):
        """Установка текущей толщины кисти"""
        self.current_thickness = thickness
    
    def set_tool(self, tool: str):
        """Установка текущего инструмента"""
        self.current_tool = tool
    
    def resize(self, width: int, height: int):
        """Изменение размера холста"""
        self.width = width
        self.height = height
        
        new_image = QImage(width, height, QImage.Format.Format_ARGB32)
        new_image.fill(self.background_color)
        
        painter = QPainter(new_image)
        painter.drawImage(0, 0, self._image)
        painter.end()
        
        self._image = new_image
    
    def _rebuild_image(self):
        """Перерисовка изображения на основе истории штрихов"""
        self._image.fill(self.background_color)
        
        painter = QPainter(self._image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for stroke in self.undo_stack:
            self._draw_stroke(painter, stroke)
        
        painter.end()
    
    def _draw_stroke(self, painter: QPainter, stroke: Stroke):
        """Отрисовка одного штриха"""
        if len(stroke.points) < 2:
            return
            
        pen = QPen(stroke.color)
        pen.setWidthF(stroke.thickness)
        pen.setCapStyle(QPen.CapStyle.RoundCap)
        pen.setJoinStyle(QPen.JoinStyle.RoundJoin)
        
        painter.setPen(pen)
        
        for i in range(len(stroke.points) - 1):
            painter.drawLine(stroke.points[i], stroke.points[i + 1])
    
    @property
    def image(self) -> QImage:
        """Получение текущего изображения холста"""
        return self._image


class RenderEngine:
    """Движок для базовой отрисовки холста"""
    
    def __init__(self, canvas_model: CanvasModel):
        self.canvas_model = canvas_model
    
    def render_to_painter(self, painter: QPainter, target_rect: QRectF):
        """Отрисовка холста на QPainter"""
        # Отрисовываем основное изображение холста
        source_rect = QRectF(0, 0, self.canvas_model.width, self.canvas_model.height)
        painter.drawImage(target_rect, self.canvas_model.image, source_rect)
        
        # Отрисовываем текущий активный штрих
        if self.canvas_model.current_stroke:
            self._draw_current_stroke(painter)
    
    def _draw_current_stroke(self, painter: QPainter):
        """Отрисовка текущего активного штриха"""
        stroke = self.canvas_model.current_stroke
        if len(stroke.points) < 2:
            return
        
        pen = QPen(stroke.color)
        pen.setWidthF(stroke.thickness)
        pen.setCapStyle(QPen.CapStyle.RoundCap)
        pen.setJoinStyle(QPen.JoinStyle.RoundJoin)
        
        painter.setPen(pen)
        
        for i in range(len(stroke.points) - 1):
            painter.drawLine(stroke.points[i], stroke.points[i + 1])
