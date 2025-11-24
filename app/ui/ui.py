"""
Intelligent Canvas - UI Prototype (Week 2)

Changes for Week 2 (Хамитов Дамир):
- Улучшенные панели инструментов (Brush, Eraser, Fill, Picker) with keyboard shortcuts
- Явный визуальный индикатор активного режима (иконка + текст) в верхней панели
- Активное состояние для образцов цвета и размера кисти (подсветка)
- Обновление индикатора текущего цвета через setter (без прямого доступа к приватным полям)
- Небольшие UX-улучшения: быстрый сброс режима Fill после применения, фокус клавиатуры
"""

import sys
import random
from typing import Optional, Dict

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QPixmap, QPaintEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy, QStatusBar,
    QFileDialog, QDialog, QCheckBox, QComboBox, QSlider, QDialogButtonBox
)

from app.vision.camera_service import CameraService

# --- Stub Classes for Future Integration ---
class CanvasModel:
    """Заглушка модели холста. В будущем будет хранить данные о рисунке."""
    def __init__(self):
        self.background_color: Optional[QColor] = None

class RenderEngine:
    """Заглушка движка рендеринга. В будущем будет отвечать за отрисовку."""
    pass

class HandTrackingService:
    """Заглушка сервиса отслеживания рук."""
    def get_fps(self) -> int:
        # В будущем будет возвращать реальный FPS из видеопотока
        return random.randint(55, 60)
# --- End of Stub Classes ---


class CanvasWidget(QWidget):
    """
    Виджет холста. Поддерживает заполнение фона цветом.
    Подготовлен для интеграции с RenderEngine и CanvasModel.
    """
    def __init__(self, canvas_model: CanvasModel, parent=None):
        super().__init__(parent)
        self._model = canvas_model
        self._render_engine = RenderEngine()  # Заглушка
        self.setMinimumSize(900, 600)
        self.show_grid = True
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._grid_pixmap: Optional[QPixmap] = None
        self.setStyleSheet("background-color: #F3F5F7;")  # Базовый фон
        self._grid_step = 80

    def fill_with_color(self, color_hex: str) -> None:
        """Заполнить фон указанным цветом (hex string)."""
        try:
            self._model.background_color = QColor(color_hex)
        except Exception:
            self._model.background_color = None
        self.update()

    def clear_fill(self) -> None:
        """Очистить заливку фона."""
        self._model.background_color = None
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._regen_grid()

    def _regen_grid(self) -> None:
        """(Re)Генерирует кэшированное изображение сетки."""
        w, h = max(1, self.width()), max(1, self.height())
        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(0, 0, 0, 15))
        pen.setWidth(1)
        painter.setPen(pen)
        step = getattr(self._model, "grid_step", 80) if hasattr(self._model, "grid_step") else self._grid_step

        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)
        painter.end()
        self._grid_pixmap = pix

    def paintEvent(self, event: QPaintEvent):
        """Отрисовывает фон и сетку."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Рисуем фон
        bg_color = self._model.background_color or QColor("#F3F5F7")
        painter.fillRect(self.rect(), bg_color)

        # 2. Рисуем сетку поверх фона
        if self.show_grid:
            if self._grid_pixmap is None or self._grid_pixmap.size() != self.size():
                self._regen_grid()
            if self._grid_pixmap:
                painter.drawPixmap(0, 0, self._grid_pixmap)



class ToolButton(QPushButton):
    """Кнопка инструмента с плоским дизайном."""
    def __init__(self, tooltip: str = "", icon_text: str = "", parent=None, size: int = 56):
        super().__init__(parent)
        self.setText(icon_text)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self._size = size
        self._is_active = False
        self._init_style()

    def set_active(self, active: bool) -> None:
        """Устанавливает активное/неактивное состояние кнопки."""
        self._is_active = active
        self._init_style()

    def _init_style(self):
        active_style = """
            background-color: #5A7FFF;
            color: white;
            border: 2px solid #5A7FFF;
        """ if self._is_active else ""

        inactive_style = """
            background-color: #FFFFFF;
            color: #333333;
            border: 2px solid #E0E0E0;
        """

        self.setStyleSheet(f"""
            QPushButton {{
                {active_style if self._is_active else inactive_style}
                border-radius: {self._size // 2}px;
                font-size: 20px;
                min-width: {self._size}px;
                min-height: {self._size}px;
            }}
            QPushButton:hover {{
                background-color: #F0F4FF;
                border: 2px solid #5A7FFF;
            }}
            QPushButton:pressed {{
                background-color: #E0EAFF;
            }}
        """)


class ColorSwatchButton(ToolButton):
    """Кнопка-образец цвета с возможностью пометить как выбранную."""
    def __init__(self, color_hex: str = "#3498DB", tooltip: str = "", size: int = 44, parent=None):
        self._color_hex = color_hex
        super().__init__(tooltip=tooltip or color_hex, icon_text="", parent=parent, size=size)
        self._is_selected = False
        self._init_style()

    @property
    def color_hex(self) -> str:
        return self._color_hex

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._init_style()

    def _init_style(self):
        # выделяем белой рамкой если выбран
        border = "2px solid #FFFFFF" if not getattr(self, '_is_selected', False) else "3px solid #5A7FFF"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color_hex};
                border: {border};
                border-radius: {self._size // 2}px;
                min-width: {self._size}px;
                min-height: {self._size}px;
            }}
            QPushButton:hover {{
                border: 2px solid #5A7FFF;
            }}
        """)


class BrushSizeButton(ToolButton):
    """Кнопка для выбора размера кисти."""
    def __init__(self, size_px: int, parent=None):
        super().__init__(tooltip=f"Кисть: {size_px}px", icon_text="", parent=parent, size=70)
        self.brush_size = size_px

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        radius = max(3.0, float(self.brush_size) / 2.0)
        color = QColor(60, 60, 60) if not self._is_active else QColor(255, 255, 255)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, radius, radius)
        painter.end()


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    def __init__(self):
        super().__init__()
        self._canvas_model = CanvasModel()
        self._hand_tracker = HandTrackingService()

        self._current_tool = "Brush"
        self._current_color = "#3498DB"
        self._current_brush_size = 12

        # UI state references
        self._tool_buttons: Dict[str, ToolButton] = {}
        self._color_swatches: list[ColorSwatchButton] = []
        self._brush_size_buttons: list[BrushSizeButton] = []

        self._camera = CameraService()
        self._vision_timer = QTimer(self)
        self._vision_timer.timeout.connect(self._update_from_camera)
        self._vision_timer.start(16)  # ~60 FPS

        self._init_ui()
        self._setup_timers()

    def _save_canvas(self):
        """Сохраняет видимое содержимое холста как PNG."""
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить изображение", "", "PNG Files (*.png)")
        if not path:
            return

        pixmap = self.canvas_widget.grab()
        pixmap.save(path, "PNG")
        self.status_bar.showMessage(f"Файл сохранён: {path}")

    def _open_image(self):
        """Открывает изображение и устанавливает его как фон."""
        path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", "", "Images (*.png *.jpg)")
        if not path:
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.status_bar.showMessage("Не удалось открыть файл.")
            return

        # Берём средний цвет картинки для фона (т.к. кистей ещё нет)
        avg = pixmap.scaled(1, 1).toImage().pixelColor(0, 0).name()
        self.canvas_widget.fill_with_color(avg)
        self.status_bar.showMessage(f"Фон установлен из файла: {path}")

    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        self.setWindowTitle("Intelligent Canvas — Prototype (Week 2)")
        self.resize(1400, 900)
        self.setStyleSheet("QMainWindow { background-color: #E9EEF3; }")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Верхняя панель: палитра цветов + индикатор режима
        self._create_top_palette_bar(main_layout)

        self._create_application_status_bar()
        
        # 2. Центральная область
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(12)
        self._create_left_toolbar(middle_layout)
        self._create_central_canvas(middle_layout)
        self._create_right_control_panel(middle_layout)
        main_layout.addLayout(middle_layout, stretch=1)

        # 3. Нижняя панель
        self._create_bottom_status_bar(main_layout)


    def _create_top_palette_bar(self, parent_layout: QVBoxLayout) -> None:
        """Создает верхнюю панель с палитрой цветов и индикатором активного режима."""
        palette_frame = QFrame()
        palette_frame.setFixedHeight(96)
        palette_frame.setStyleSheet("QFrame { background: #2C3E50; border-radius: 8px; }")
        palette_layout = QHBoxLayout(palette_frame)
        palette_layout.setContentsMargins(18, 12, 18, 12)
        palette_layout.setSpacing(14)

        # Индикатор активного режима (иконка + текст)
        self._active_mode_label = QLabel("🖌 Brush")
        self._active_mode_label.setStyleSheet("color: #ECF0F1; font-weight: 700; font-size: 16px;")
        palette_layout.addWidget(self._active_mode_label)

        # Контейнер для образцов цвета
        swatches_container = QWidget()
        swatches_layout = QHBoxLayout(swatches_container)
        swatches_layout.setContentsMargins(0, 0, 0, 0)
        swatches_layout.setSpacing(10)
        swatches_layout.setAlignment(Qt.AlignCenter)

        colors = ["#FF4757", "#FF7A3D", "#FFC312", "#2ECC71",
                  "#3498DB", "#9B59B6", "#E91E63", "#2C3E50"]
        for color_hex in colors:
            swatch = ColorSwatchButton(color_hex, tooltip=color_hex)
            swatch.clicked.connect(lambda checked, col=color_hex, btn=swatch: self._on_color_swatch_clicked(col, btn))
            swatches_layout.addWidget(swatch)
            self._color_swatches.append(swatch)

        palette_layout.addWidget(swatches_container, stretch=1)

        # Индикатор текущего цвета
        self._current_color_indicator = ColorSwatchButton(self._current_color, "Текущий цвет", 44)
        self._current_color_indicator.setEnabled(False)
        # отметить текущий цвет среди образцов если совпадает
        for s in self._color_swatches:
            s.set_selected(s.color_hex.lower() == self._current_color.lower())
        palette_layout.addWidget(self._current_color_indicator)

        # Кнопка "Настроить цвета" вместо "Режим заливки"
        self._custom_colors_btn = QPushButton("🎨 Настроить цвета")
        self._custom_colors_btn.setToolTip("Открыть диалог настройки пользовательских цветов")
        self._custom_colors_btn.clicked.connect(self._on_custom_colors_clicked)
        self._custom_colors_btn.setFixedHeight(40)
        self._custom_colors_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495E;
                color: #ECF0F1;
                border: 2px solid #5A7FFF;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4A6FCC;
            }
        """)
        palette_layout.addWidget(self._custom_colors_btn)

        parent_layout.addWidget(palette_frame)

    def _create_left_toolbar(self, parent_layout: QHBoxLayout) -> None:
        """Создает левую панель инструментов."""
        toolbar_container = QFrame()
        toolbar_container.setFixedWidth(92)
        toolbar_container.setStyleSheet("QFrame { background: transparent; }")
        toolbar_layout = QVBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(6, 6, 6, 6)
        toolbar_layout.setSpacing(14)

        tools = [
            ("Brush", "🖌", "Кисть (B)"),
            ("Eraser", "🧽", "Ластик (E)")
        ]
        for tool_id, icon, tooltip in tools:
            btn = ToolButton(tooltip, icon, size=56)
            btn.setProperty('tool_id', tool_id)
            btn.clicked.connect(self._on_tool_selected)
            toolbar_layout.addWidget(btn)
            self._tool_buttons[tool_id] = btn

        toolbar_layout.addStretch()
        parent_layout.addWidget(toolbar_container)
        self._set_active_tool("Brush")

    def _create_central_canvas(self, parent_layout: QHBoxLayout) -> None:
        """Создает центральный виджет холста."""
        self.canvas_widget = CanvasWidget(self._canvas_model)
        parent_layout.addWidget(self.canvas_widget, stretch=1)

    def _create_right_control_panel(self, parent_layout: QHBoxLayout) -> None:
        """Создает правую панель управления."""
        control_container = QFrame()
        control_container.setFixedWidth(96)
        control_container.setStyleSheet("QFrame { background: transparent; }")
        control_layout = QVBoxLayout(control_container)
        control_layout.setContentsMargins(6, 6, 6, 6)
        control_layout.setSpacing(12)

        controls = [
            ("Save", "💾", "Сохранить"),
            ("Open", "📁", "Открыть"),
            ("Undo", "↶", "Отменить (Ctrl+Z)"),
            ("Redo", "↷", "Повторить (Ctrl+Y)"),
            ("Clear", "🗑", "Очистить холст")
        ]
        for ctrl_id, icon, tooltip in controls:
            btn = ToolButton(tooltip, icon, size=56)
            btn.clicked.connect(lambda checked, cid=ctrl_id: self._on_control_action(cid))
            control_layout.addWidget(btn)

        control_layout.addStretch()

        settings_btn = ToolButton("Настройки", "⚙", size=56)
        settings_btn.clicked.connect(lambda: self._on_control_action("Settings"))
        control_layout.addWidget(settings_btn)

        parent_layout.addWidget(control_container)

    def _open_mini_tool_overlay(self, x, y):
        if not hasattr(self, "_mini_overlay"):
            self._mini_overlay = MiniToolOverlay(self)

        self._mini_overlay.show_at(x, y)

    def _create_bottom_status_bar(self, parent_layout: QVBoxLayout) -> None:
        """Создает нижнюю информационную панель."""
        info_frame = QFrame()
        info_frame.setFixedHeight(110)
        info_frame.setStyleSheet("QFrame { background: #FFFFFF; border: 2px solid #E0E0E0; border-radius: 8px; }")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(12)

        gesture_hint = QLabel("Информация")
        gesture_hint.setStyleSheet("color: #334152; font-size: 13px;")
        info_layout.addWidget(gesture_hint)
        info_layout.addStretch()

        brush_label = QLabel("Размер кисти:")
        brush_label.setStyleSheet("color: #23303a; font-weight: 600;")
        info_layout.addWidget(brush_label)

        for size in (6, 12, 20, 36):
            btn = BrushSizeButton(size)
            btn.clicked.connect(lambda checked, s=size, b=btn: self._on_brush_size_selected(s, b))
            info_layout.addWidget(btn)
            self._brush_size_buttons.append(btn)

        fps_widget = self._create_fps_widget()
        info_layout.addWidget(fps_widget)

        parent_layout.addWidget(info_frame)

        self.gesture_hint_widget = GestureHintWidget()
        info_layout.addWidget(self.gesture_hint_widget)

        # отметить текущий размер кисти
        self._update_brush_size_buttons()

    def _update_from_camera(self):
        frame = self._camera.get_frame_data()
        if frame is None:
            return

        # Обновляем подсказку жестов
        self.gesture_hint_widget.update_hint(frame.gesture)

        # Обновляем подсветку в UI
        if frame.gesture == "drawing":
            self._set_active_tool("Brush")
        elif frame.gesture == "erasing":
            self._set_active_tool("Eraser")
        elif frame.gesture == "scale":
            pass  # масштабирование будет на 5 неделе
        elif frame.gesture == "menu":
            self._open_mini_tool_overlay(frame.index_finger_x, frame.index_finger_y)

        if frame.gesture != "menu" and hasattr(self, "_mini_overlay"):
            self._mini_overlay.hide()

    def _create_fps_widget(self) -> QFrame:
        """Создает виджет для отображения FPS."""
        fps_frame = QFrame()
        fps_frame.setFixedSize(84, 56)
        fps_frame.setStyleSheet("""
            QFrame {
                background: #27AE60;
                border: 2px solid #219653;
                border-radius: 8px;
            }
        """)
        fps_layout = QVBoxLayout(fps_frame)
        fps_layout.setContentsMargins(4, 4, 4, 4)
        self.fps_value_label = QLabel("60")
        self.fps_value_label.setAlignment(Qt.AlignCenter)
        self.fps_value_label.setStyleSheet("color: white; font-weight: 700; font-size: 20px;")
        fps_text_label = QLabel("FPS")
        fps_text_label.setAlignment(Qt.AlignCenter)
        fps_text_label.setStyleSheet("color: white; font-size: 10px;")
        fps_layout.addWidget(self.fps_value_label)
        fps_layout.addWidget(fps_text_label)
        return fps_frame

    def _create_application_status_bar(self) -> None:
        """Создает строку состояния приложения."""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { background: #FFFFFF; color: #2C3E50; padding: 6px; border-top: 1px solid #E0E0E0; }")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов. Используйте жесты для рисования.")

    def _setup_timers(self) -> None:
        """Настраивает таймеры для обновления UI."""
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps_display)
        self._fps_timer.start(500)

    def _update_fps_display(self) -> None:
        """Обновляет значение FPS в UI."""
        current_fps = self._hand_tracker.get_fps()
        self.fps_value_label.setText(str(current_fps))

    # --- Обработчики событий ---
    def _on_tool_selected(self) -> None:
        """Обрабатывает выбор инструмента."""
        clicked_button = self.sender()
        tool_id = clicked_button.property('tool_id')
        self._set_active_tool(tool_id)

    def _set_active_tool(self, tool_id: str) -> None:
        """Устанавливает активный инструмент и обновляет UI-индикатор."""
        # сброс старого режима Fill если пользователь снова выбирает тот же инструмент (toggle off)
        previous = self._current_tool
        self._current_tool = tool_id
        for tid, btn in self._tool_buttons.items():
            btn.set_active(tid == tool_id)

        # Обновляем верхний индикатор
        icon = self._tool_buttons.get(tool_id).text() if tool_id in self._tool_buttons else ""
        self._active_mode_label.setText(f"{icon} {tool_id}")
        self.status_bar.showMessage(f"Активный инструмент: {tool_id}")

    def _on_control_action(self, action_id: str) -> None:
        if action_id == "Save":
            self._save_canvas()
            return

        if action_id == "Open":
            self._open_image()
            return

        if action_id == "Settings":
            dlg = SettingsDialog(self, self.canvas_widget)
            dlg.exec()
            return

        if action_id == "Clear":
            self.canvas_widget.clear_fill()
            self.status_bar.showMessage("Холст очищен.")
            return


    def _on_brush_size_selected(self, size: int, btn: BrushSizeButton) -> None:
        """Обрабатывает выбор размера кисти и отмечает выбранную кнопку."""
        self._current_brush_size = size
        self._update_brush_size_buttons()
        self.status_bar.showMessage(f"Размер кисти изменен на {size}px")

    def _update_brush_size_buttons(self) -> None:
        for b in self._brush_size_buttons:
            b.set_active(b.brush_size == self._current_brush_size)

    def _on_custom_colors_clicked(self) -> None:
        """Обрабатывает клик по кнопке 'Настроить цвета' (заглушка)."""
        self.status_bar.showMessage("Диалог настройки пользовательских цветов (в разработке)")

    def _on_color_swatch_clicked(self, color_hex: str, btn: ColorSwatchButton) -> None:
        """Обрабатывает клик на образце цвета."""
        # Иначе выбираем цвет для кисти
        self._current_color = color_hex
        # обновляем индикаторы цвета
        self._current_color_indicator._color_hex = color_hex
        self._current_color_indicator._init_style()
        for s in self._color_swatches:
            s.set_selected(s is btn)
        self.status_bar.showMessage(f"Цвет кисти изменен на {color_hex}")

class SettingsDialog(QDialog):
    def __init__(self, parent, canvas_widget: CanvasWidget):
        super().__init__(parent)
        self.canvas = canvas_widget
        self.setWindowTitle("Настройки")

        layout = QVBoxLayout(self)

        # Сетка
        self.grid_check = QCheckBox("Показывать сетку")
        self.grid_check.setChecked(self.canvas.show_grid)
        layout.addWidget(self.grid_check)

        # Размер сетки
        layout.addWidget(QLabel("Размер сетки:"))
        self.grid_slider = QSlider(Qt.Horizontal)
        self.grid_slider.setRange(40, 160)
        self.grid_slider.setValue(self.canvas._grid_step)
        layout.addWidget(self.grid_slider)

        # Кнопки OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.apply_settings)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def apply_settings(self):
        # включить/выключить сетку
        self.canvas.show_grid = self.grid_check.isChecked()

        # изменить шаг сетки
        self.canvas._grid_step = self.grid_slider.value()

        # принудительное обновление
        self.canvas._grid_pixmap = None
        self.canvas.update()

        self.accept()

class GestureHintWidget(QLabel):
    """Плавающая подсказка жестов внизу."""
    def __init__(self):
        super().__init__()
        self.setText("Жесты не обнаружены")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background: #2C3E50;
                color: #ECF0F1;
                padding: 10px 20px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        self.setFixedHeight(40)

    def update_hint(self, gesture: str):
        mapping = {
            "idle": "✋ Двигайте рукой — жесты не обнаружены",
            "drawing": "🤏 Pinch — рисование",
            "erasing": "✋ Открытая ладонь — ластик",
            "scale": "🤌 Двуручный pinch — масштабирование",
            "menu": "✊ Кулак — открыть меню",
        }
        self.setText(mapping.get(gesture, "Неизвестный жест"))

class MiniToolOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)
        self.setStyleSheet("""
            QWidget {
                background: #FFFFFF;
                border: 2px solid #5A7FFF;
                border-radius: 12px;
            }
        """)

        # инструменты
        btn1 = QPushButton("🖌")
        btn2 = QPushButton("🧽")
        btn3 = QPushButton("🎨")

        for b in (btn1, btn2, btn3):
            b.setFixedSize(48, 48)
            self.layout.addWidget(b)

        btn1.clicked.connect(lambda: parent._set_active_tool("Brush"))
        btn2.clicked.connect(lambda: parent._set_active_tool("Eraser"))
        btn3.clicked.connect(lambda: parent._on_custom_colors_clicked())

    def show_at(self, x, y):
        self.move(x, y)
        self.show()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
