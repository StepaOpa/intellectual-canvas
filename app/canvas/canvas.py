from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter


class CanvasModel:
    """Модель холста для хранения данных"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.background_color = QColor(255, 255, 255)
        
        # Изображение холста
        self._image = QImage(width, height, QImage.Format.Format_ARGB32)
        self._image.fill(self.background_color)
    
    def clear(self):
        """Очистка холста"""
        self._image.fill(self.background_color)
    
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
