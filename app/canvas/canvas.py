from dataclasses import dataclass, field
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QTransform
import os


@dataclass
class Stroke:
    """Класс для представления одного штриха на холсте"""
    points: List[QPointF] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor(0, 0, 0))
    thickness: float = 3.0
    tool: str = "brush"  # "brush" или "eraser"


class CanvasModel:
    """Модель холста для хранения данных и управления рисованием"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.background_color = QColor(255, 255, 255)
        self.background_image: Optional[QImage] = None
        
        # История штрихов для undo/redo
        self.strokes: List[Stroke] = []
        self.undo_stack: List[Stroke] = []
        self.redo_stack: List[Stroke] = []
        
        # Текущий активный штрих
        self.current_stroke: Optional[Stroke] = None
        
        # Настройки по умолчанию
        self.current_color = QColor(0, 0, 0)
        self.current_thickness = 3.0
        self.current_tool = "brush"  # "brush" или "eraser"
        
        # Изображение холста
        self._image = QImage(width, height, QImage.Format.Format_ARGB32)
        self._image.fill(self.background_color)
    
    def begin_stroke(self, pos: QPointF):
        """Начало нового штриха"""
        self.current_stroke = Stroke(
            color=self.current_color if self.current_tool == "brush" else self.background_color,
            thickness=self.current_thickness,
            tool=self.current_tool
        )
        self.current_stroke.points.append(pos)
        self.redo_stack.clear()
    
    def continue_stroke(self, pos: QPointF):
        """Продолжение текущего штриха"""
        if self.current_stroke:
            self.current_stroke.points.append(pos)
            self._draw_current_stroke()
    
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
        if self.background_image:
            self._draw_background()
    
    def load_background(self, image_path: str) -> bool:
        """Загрузка фонового изображения"""
        try:
            background = QImage(image_path)
            if background.isNull():
                return False
            
            self.background_image = background.scaled(
                self.width, self.height, 
                aspectRatioMode=1,  # KeepAspectRatio
                transformMode=1     # SmoothTransformation
            )
            self._draw_background()
            return True
        except:
            return False
    
    def set_background_color(self, color: QColor):
        """Установка цвета фона"""
        self.background_color = color
        self.background_image = None
        self._rebuild_image()
    
    def _draw_background(self):
        """Отрисовка фона"""
        if self.background_image:
            self._image.fill(Qt.transparent)
            painter = QPainter(self._image)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(0, 0, self.background_image)
            painter.end()
        else:
            self._image.fill(self.background_color)
        
        self._rebuild_image()
    
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
        
        if self.background_image:
            self.background_image = self.background_image.scaled(
                width, height, 
                aspectRatioMode=1,
                transformMode=1
            )
        
        self._rebuild_image()
    
    def _rebuild_image(self):
        """Перерисовка изображения на основе истории штрихов"""
        self._draw_background()
        
        painter = QPainter(self._image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        for stroke in self.undo_stack:
            self._draw_stroke(painter, stroke)
        
        painter.end()
    
    def _draw_current_stroke(self):
        """Отрисовка текущего активного штриха на изображении"""
        if not self.current_stroke or len(self.current_stroke.points) < 2:
            return
            
        painter = QPainter(self._image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._draw_stroke(painter, self.current_stroke)
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
    """Движок для отрисовки холста с поддержкой масштабирования и перемещения"""
    
    def __init__(self, canvas_model: CanvasModel):
        self.canvas_model = canvas_model
        self.scale_factor = 1.0
        self.offset = QPointF(0, 0)
        self._cached_image: Optional[QImage] = None
        self._cache_dirty = True
    
    def render_to_painter(self, painter: QPainter, target_rect: QRectF):
        """Отрисовка холста на QPainter с поддержкой трансформаций"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Применяем трансформации (масштаб и смещение)
        painter.save()
        painter.translate(self.offset)
        painter.scale(self.scale_factor, self.scale_factor)
        
        # Используем кэшированное изображение для плавности
        if self._cache_dirty or self._cached_image is None:
            self._update_cache()
        
        # Отрисовываем кэшированное изображение
        source_rect = QRectF(0, 0, self.canvas_model.width, self.canvas_model.height)
        painter.drawImage(target_rect, self._cached_image, source_rect)
        
        # Отрисовываем текущий активный штрих поверх
        if self.canvas_model.current_stroke:
            self._draw_current_stroke(painter)
        
        painter.restore()
    
    def _update_cache(self):
        """Обновление кэшированного изображения для плавного рендеринга"""
        self._cached_image = QImage(
            self.canvas_model.width, 
            self.canvas_model.height, 
            QImage.Format.Format_ARGB32
        )
        self._cached_image.fill(Qt.transparent)
        
        cache_painter = QPainter(self._cached_image)
        cache_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cache_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Рисуем основное изображение холста
        cache_painter.drawImage(0, 0, self.canvas_model.image)
        cache_painter.end()
        
        self._cache_dirty = False
    
    def invalidate_cache(self):
        """Пометить кэш как устаревший"""
        self._cache_dirty = True
    
    def _draw_current_stroke(self, painter: QPainter):
        """Отрисовка текущего активного штриха"""
        stroke = self.canvas_model.current_stroke
        if len(stroke.points) < 2:
            return
        
        pen = QPen(stroke.color)
        pen.setWidthF(stroke.thickness / self.scale_factor)  # Компенсируем масштаб для толщины
        pen.setCapStyle(QPen.CapStyle.RoundCap)
        pen.setJoinStyle(QPen.JoinStyle.RoundJoin)
        
        painter.setPen(pen)
        
        for i in range(len(stroke.points) - 1):
            painter.drawLine(stroke.points[i], stroke.points[i + 1])
    
    def set_scale(self, scale: float, center: QPointF = None):
        """Установка масштаба относительно центра"""
        old_scale = self.scale_factor
        self.scale_factor = max(0.1, min(5.0, scale))  # Ограничиваем масштаб
        
        # Корректируем смещение для масштабирования относительно центра
        if center and old_scale != 0:
            scale_ratio = self.scale_factor / old_scale
            self.offset = center + (self.offset - center) * scale_ratio
        
        self.invalidate_cache()
    
    def zoom_in(self, center: QPointF = None):
        """Увеличение масштаба"""
        self.set_scale(self.scale_factor * 1.2, center)
    
    def zoom_out(self, center: QPointF = None):
        """Уменьшение масштаба"""
        self.set_scale(self.scale_factor / 1.2, center)
    
    def reset_view(self):
        """Сброс вида к исходному состоянию"""
        self.scale_factor = 1.0
        self.offset = QPointF(0, 0)
        self.invalidate_cache()
    
    def pan(self, delta: QPointF):
        """Перемещение холста"""
        self.offset += delta
        self.invalidate_cache()
    
    def screen_to_canvas(self, screen_pos: QPointF) -> QPointF:
        """Преобразование экранных координат в координаты холста"""
        if self.scale_factor == 0:
            return screen_pos
        
        return (screen_pos - self.offset) / self.scale_factor
    
    def canvas_to_screen(self, canvas_pos: QPointF) -> QPointF:
        """Преобразование координат холста в экранные координаты"""
        return canvas_pos * self.scale_factor + self.offset
    
    def get_visible_rect(self) -> QRectF:
        """Получение видимой области холста в координатах холста"""
        if self.scale_factor == 0:
            return QRectF()
        
        # Это нужно вычислять на основе размера виджета
        return QRectF(0, 0, self.canvas_model.width, self.canvas_model.height)
    
    def export_to_png(self, filename: str) -> bool:
        """Экспорт холста в PNG"""
        try:
            return self.canvas_model.image.save(filename, "PNG")
        except:
            return False
    
    def export_to_svg(self, filename: str) -> bool:
        """Экспорт холста в SVG"""
        try:
            from PySide6.QtSvg import QSvgGenerator
            from PySide6.QtCore import QRect
            
            generator = QSvgGenerator()
            generator.setFileName(filename)
            generator.setSize(self.canvas_model.image.size())
            generator.setViewBox(QRect(0, 0, self.canvas_model.width, self.canvas_model.height))
            generator.setTitle("Intelligent Canvas Export")
            generator.setDescription("Exported from Intelligent Canvas Application")
            
            painter = QPainter(generator)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if self.canvas_model.background_image:
                painter.drawImage(0, 0, self.canvas_model.background_image)
            else:
                painter.fillRect(0, 0, self.canvas_model.width, self.canvas_model.height, 
                               self.canvas_model.background_color)
            
            for stroke in self.canvas_model.undo_stack:
                pen = QPen(stroke.color)
                pen.setWidthF(stroke.thickness)
                pen.setCapStyle(QPen.CapStyle.RoundCap)
                pen.setJoinStyle(QPen.JoinStyle.RoundJoin)
                painter.setPen(pen)
                
                for i in range(len(stroke.points) - 1):
                    painter.drawLine(stroke.points[i], stroke.points[i + 1])
            
            painter.end()
            return True
        except:
            return False
