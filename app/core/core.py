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
        # Холст в 2 раза больше разрешения камеры для четкости
        self.scale_ratio = 2.0
        self.model_width = int(self.cam_width * self.scale_ratio)
        self.model_height = int(self.cam_height * self.scale_ratio)
        
        self.model = CanvasModel(width=self.model_width, height=self.model_height)
        self.engine = RenderEngine(self.model)
        
        # 3. Создаем окно
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
        
        # A. Отрисовка камеры и индикаторов
        if data.raw_frame is not None:
            # Зеркалим кадр (как в зеркале)
            display_frame = cv2.flip(data.raw_frame, 1)
            
            # --- ОТРИСОВКА ИНДИКАТОРА (ПОЛУПРОЗРАЧНЫЙ КРУГ) ---
            if data.cursor_x != -1:
                # 1. Создаем слой для рисования (overlay)
                overlay = display_frame.copy()
                
                # 2. Координаты (инвертируем X из-за зеркалирования)
                cv_draw_x = self.cam_width - data.cursor_x
                cv_draw_y = data.cursor_y
                
                # 3. Вычисляем радиус визуального индикатора
                # Размер кисти задан в пикселях Холста. 
                # Нам нужно перевести его в пиксели Камеры.
                # Radius = (Thickness / Scale) / 2
                visual_radius = int((self.model.current_thickness / self.scale_ratio) / 2)
                visual_radius = max(3, visual_radius) # Минимальный размер, чтобы было видно
                
                # 4. Цвет и прозрачность
                if data.gesture == "erasing":
                    color = (0, 0, 255) # Красный (BGR) для ластика
                    alpha = 0.4         # Более прозрачный
                else:
                    color = (0, 255, 0) # Зеленый (BGR) для кисти
                    alpha = 0.5         # 50% прозрачности

                # 5. Рисуем заполненный круг на слое overlay
                # cv2.LINE_AA делает края сглаженными (ровными)
                cv2.circle(overlay, (cv_draw_x, cv_draw_y), visual_radius, color, -1, cv2.LINE_AA)
                
                # 6. Смешиваем слои: result = overlay * alpha + frame * (1 - alpha)
                cv2.addWeighted(overlay, alpha, display_frame, 1 - alpha, 0, display_frame)
                
                # 7. Рисуем маленькую белую точку в центре для точности
                cv2.circle(display_frame, (cv_draw_x, cv_draw_y), 2, (255, 255, 255), -1, cv2.LINE_AA)

            # Конвертация в формат Qt
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            self.model.set_camera_frame(qt_image.copy())

        # B. Обновление UI
        self.window.update_gesture_hint(data.gesture)
        
        # Если рука не обнаружена
        if data.cursor_x == -1 or data.cursor_y == -1:
            if self.model.current_stroke:
                self.model.end_stroke()
            self.window.canvas_widget.update()
            return

        # C. Координаты (0..1 -> Холст)
        norm_x = 1.0 - (data.cursor_x / self.cam_width)
        norm_y = data.cursor_y / self.cam_height
        
        canvas_pos = QPointF(norm_x * self.model.width, norm_y * self.model.height)

        # D. Логика рисования
        if self.model.current_stroke:
            is_consistent = False
            if self.model.current_tool == "brush" and data.gesture == "drawing":
                is_consistent = True
            elif self.model.current_tool == "eraser" and data.gesture == "erasing":
                is_consistent = True
            
            if is_consistent:
                self.model.continue_stroke(canvas_pos)
            else:
                self.model.end_stroke()
                
            self.window.canvas_widget.update()
        else:
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
            
            self.window.canvas_widget.update()