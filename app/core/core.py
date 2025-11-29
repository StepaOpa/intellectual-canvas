import sys
import cv2
from PySide6.QtCore import QTimer, QPointF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from app.canvas.canvas import CanvasModel, RenderEngine
from app.ui.ui import MainWindow
from app.vision.camera_service import CameraService

class AppCore:
    def __init__(self, sys_argv):
        self.app = QApplication(sys_argv)
        self.app.setStyle("Fusion")
        
        # 1. Инициализация камеры
        try:
            # Запрашиваем стандартное разрешение 640x480
            self.cam_width = 640
            self.cam_height = 480
            self.camera = CameraService(camera_index=0, resolution=(self.cam_width, self.cam_height))
            self.camera_available = True
            print("Camera initialized successfully.")
        except Exception as e:
            print(f"Camera error: {e}. Running in mouse-only mode.")
            self.camera_available = False
            self.cam_width, self.cam_height = 800, 600 # Fallback

        # 2. Настраиваем модель под размер камеры
        # Для лучшего качества рисования можно увеличить разрешение холста, сохраняя пропорции
        # Например, удвоим разрешение: 1280x960
        scale_ratio = 2
        self.model_width = self.cam_width * scale_ratio
        self.model_height = self.cam_height * scale_ratio
        
        self.model = CanvasModel(width=self.model_width, height=self.model_height)
        self.engine = RenderEngine(self.model)
        
        # 3. Создаем окно
        self.window = MainWindow(self.model, self.engine)
        
        # 4. Масштабируем окно под пропорции камеры
        # Добавляем отступы на UI панели (примерно 300px по ширине и 150 по высоте)
        ui_padding_w = 250 
        ui_padding_h = 150
        target_w = self.model_width + ui_padding_w
        target_h = self.model_height + ui_padding_h
        
        # Ограничиваем, если экран слишком маленький
        if target_w > 1600: target_w = 1600
        if target_h > 1000: target_h = 1000
        
        self.window.resize(target_w, target_h)
        self.window.show()

        # 5. Таймер
        self.timer = QTimer()
        self.timer.timeout.connect(self._game_loop)
        if self.camera_available:
            self.timer.start(16)

    def run(self):
        return self.app.exec()

    def _game_loop(self):
        if not self.camera_available: return

        data = self.camera.get_frame_data()
        
        # A. Обработка изображения для фона (Отрисовка камеры)
        if data.raw_frame is not None:
            # OpenCV (BGR) -> Qt (RGB)
            # Флипаем горизонтально, чтобы работало как зеркало (интуитивнее для рисования)
            rgb_frame = cv2.cvtColor(cv2.flip(data.raw_frame, 1), cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            # Копируем, чтобы данные не исчезли
            self.model.set_camera_frame(qt_image.copy())

        # B. Обновление UI
        self.window.update_fps(data.fps)
        self.window.update_gesture_hint(data.gesture)
        
        # C. Логика координат
        # Координаты пальца приходят нормализованными (если мы их нормализуем)
        # или в пикселях камеры (0..640).
        
        # Нормализуем 0..1
        norm_x = data.index_finger_x / self.cam_width
        norm_y = data.index_finger_y / self.cam_height
        
        # Инвертируем X, так как камеру мы тоже флипнули визуально
        norm_x = 1.0 - norm_x 

        # Маппинг на размер холста
        # ВАЖНО: Мы рисуем на model.width/height. 
        # RenderEngine сам растягивает это на экран виджета.
        canvas_x = norm_x * self.model.width
        canvas_y = norm_y * self.model.height
        canvas_pos = QPointF(canvas_x, canvas_y)

        # D. Управление рисованием (Блокировка переключения во время штриха)
        if self.model.current_stroke:
            if data.gesture in ["drawing", "erasing"]:
                self.model.continue_stroke(canvas_pos)
            else:
                self.model.end_stroke()
            self.window.canvas_widget.update()
        else:
            if data.gesture == "drawing":
                if self.model.current_tool != "brush": self.window.set_tool("Brush")
                self.model.begin_stroke(canvas_pos)
                self.window.canvas_widget.update()

            elif data.gesture == "erasing":
                if self.model.current_tool != "eraser": self.window.set_tool("Eraser")
                self.model.begin_stroke(canvas_pos)
                self.window.canvas_widget.update()
            
            # Принудительно обновляем виджет, даже если не рисуем, чтобы видеть камеру (FPS)
            self.window.canvas_widget.update()