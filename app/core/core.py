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

        try:
            self.cam_width = 640
            self.cam_height = 480
            self.camera = CameraService(
                camera_index=0, resolution=(self.cam_width, self.cam_height)
            )
            self.camera_available = True
        except Exception as e:
            import traceback

            print(f"Camera error: {e}. Running in mouse-only mode.")
            print("Camera error:")
            traceback.print_exc()
            self.camera_available = False
            self.cam_width, self.cam_height = 800, 600

        self.scale_ratio = 2.0
        self.model_width = int(self.cam_width * self.scale_ratio)
        self.model_height = int(self.cam_height * self.scale_ratio)

        self.model = CanvasModel(width=self.model_width, height=self.model_height)
        self.engine = RenderEngine(self.model)

        self.window = MainWindow(self.model, self.engine)

        ui_padding_w = 260
        ui_padding_h = 160
        target_w = min(1600, self.model_width + ui_padding_w)
        target_h = min(1000, self.model_height + ui_padding_h)

        self.window.resize(target_w, target_h)
        self.window.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self._game_loop)
        if self.camera_available:
            self.timer.start(16)

    def run(self):
        return self.app.exec()

    def _game_loop(self):
        if not self.camera_available:
            return

        data = self.camera.get_frame_data()

        # --- ФИЛЬТРАЦИЯ ОТКЛЮЧЕННЫХ ЖЕСТОВ ---
        if data.gesture == "drawing" and not self.model.allow_drawing:
            data.gesture = "idle"
            data.cursor_x = -1
            data.cursor_y = -1

        if data.gesture == "erasing" and not self.model.allow_erasing:
            data.gesture = "idle"
            data.cursor_x = -1
            data.cursor_y = -1

        # --- РАСЧЕТ КООРДИНАТ ---
        if data.cursor_x != -1:
            # Зеркалим X, так как камера обычно отзеркалена для удобства
            cv_draw_x = self.cam_width - data.cursor_x
            cv_draw_y = data.cursor_y

            norm_x = cv_draw_x / self.cam_width
            norm_y = cv_draw_y / self.cam_height

            model_x = norm_x * self.model.width
            model_y = norm_y * self.model.height
            canvas_pos = QPointF(model_x, model_y)
        else:
            canvas_pos = QPointF(-1, -1)

        # --- ОБНОВЛЕНИЕ КАРТИНКИ КАМЕРЫ ---
        if data.raw_frame is not None:
            # Просто зеркалим фрейм.
            # ВАЖНО: Мы НЕ рисуем здесь cv2.circle.
            # Курсор рисует RenderEngine поверх всего.
            display_frame = cv2.flip(data.raw_frame, 1)

            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            self.model.set_camera_frame(qt_image.copy())

        # --- ПЕРЕДАЕМ ДАННЫЕ О КУРСОРЕ В МОДЕЛЬ ---
        # Модель сохранит эти данные, а RenderEngine отрисует их поверх слоев
        self.model.update_cursor(canvas_pos.x(), canvas_pos.y(), data.gesture)

        # --- ОБНОВЛЕНИЕ UI ---
        self.window.update_gesture_hint(data.gesture)

        # Если рука потеряна или жест невалиден
        if data.cursor_x == -1 or data.cursor_y == -1:
            if self.model.current_stroke:
                self.model.end_stroke()
            self.window.canvas_widget.update()
            return

        # --- ЛОГИКА РИСОВАНИЯ ---
        if self.model.current_stroke:
            # Проверяем, не сменился ли жест внезапно
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
            # Начинаем новый штрих
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
