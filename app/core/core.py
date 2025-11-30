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
            self.cam_width = 640
            self.cam_height = 480
            self.camera = CameraService(camera_index=0, resolution=(self.cam_width, self.cam_height))
            self.camera_available = True
        except Exception as e:
            print(f"Camera error: {e}. Running in mouse-only mode.")
            self.camera_available = False
            self.cam_width, self.cam_height = 800, 600

        # 2. Настройка модели под пропорции камеры
        scale_ratio = 2
        self.model_width = self.cam_width * scale_ratio
        self.model_height = self.cam_height * scale_ratio
        
        self.model = CanvasModel(width=self.model_width, height=self.model_height)
        self.engine = RenderEngine(self.model)
        
        # 3. Создаем окно и масштабируем его
        self.window = MainWindow(self.model, self.engine)
        
        ui_padding_w = 260
        ui_padding_h = 160
        target_w = min(1600, self.model_width + ui_padding_w)
        target_h = min(1000, self.model_height + ui_padding_h)
        
        self.window.resize(target_w, target_h)
        self.window.show()

        # 4. Таймер
        self.timer = QTimer()
        self.timer.timeout.connect(self._game_loop)
        if self.camera_available:
            self.timer.start(16)

    def run(self):
        return self.app.exec()

    def _game_loop(self):
        if not self.camera_available: return

        data = self.camera.get_frame_data()
        
        # A. Отрисовка камеры (Фон)
        if data.raw_frame is not None:
            # Зеркалим и конвертируем
            rgb_frame = cv2.cvtColor(cv2.flip(data.raw_frame, 1), cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            self.model.set_camera_frame(qt_image.copy())

        # B. Обновление UI
        self.window.update_fps(data.fps)
        self.window.update_gesture_hint(data.gesture)
        
        # C. Координаты (0..1 -> Холст)
        norm_x = 1.0 - (data.index_finger_x / self.cam_width)
        norm_y = data.index_finger_y / self.cam_height
        
        canvas_pos = QPointF(norm_x * self.model.width, norm_y * self.model.height)

        # D. Логика рисования (ИСПРАВЛЕНО)
        if self.model.current_stroke:
            # Если мы уже рисуем штрих, проверяем, совпадает ли жест с инструментом
            is_consistent = False
            
            if self.model.current_tool == "brush" and data.gesture == "drawing":
                is_consistent = True
            elif self.model.current_tool == "eraser" and data.gesture == "erasing":
                is_consistent = True
            
            if is_consistent:
                # Продолжаем штрих
                self.model.continue_stroke(canvas_pos)
            else:
                # Жест изменился (например Pinch -> Open Palm) -> ОБРЫВАЕМ штрих
                self.model.end_stroke()
                
            self.window.canvas_widget.update()
            
        else:
            # Штриха нет, ищем начало нового
            if data.gesture == "drawing":
                if self.model.current_tool != "brush": 
                    self.window.set_tool("Brush")
                self.model.begin_stroke(canvas_pos)
                self.window.canvas_widget.update()

            elif data.gesture == "erasing":
                if self.model.current_tool != "eraser": 
                    self.window.set_tool("Eraser")
                self.model.begin_stroke(canvas_pos)
                self.window.canvas_widget.update()
            
            # Обновляем виджет, чтобы видео не фризило когда не рисуем
            self.window.canvas_widget.update()