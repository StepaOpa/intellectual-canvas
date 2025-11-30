from typing import Optional, Dict, List
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QPaintEvent, QMouseEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy, QStatusBar,
    QFileDialog, QDialog, QCheckBox, QSlider, QDialogButtonBox, QMessageBox
)

from app.canvas.canvas import CanvasModel, RenderEngine

class CanvasWidget(QWidget):
    def __init__(self, model: CanvasModel, engine: RenderEngine, parent=None):
        super().__init__(parent)
        self._model = model
        self._engine = engine
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._engine.render_to_painter(painter, self.rect())
        if self._model.show_grid:
            self._draw_grid(painter)

    def _draw_grid(self, painter: QPainter):
        step = self._model.grid_step * self._engine.scale_factor
        if step < 20: return 
        pen = QPen(QColor(0, 0, 0, 15))
        pen.setWidth(1)
        painter.setPen(pen)
        w, h = self.width(), self.height()
        for x in range(0, w, int(step)):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, int(step)):
            painter.drawLine(0, y, w, y)

    def mousePressEvent(self, event: QMouseEvent): pass 
    def mouseMoveEvent(self, event: QMouseEvent): pass
    def mouseReleaseEvent(self, event: QMouseEvent): pass


class ToolButton(QPushButton):
    def __init__(self, tooltip: str, icon_text: str, parent=None, size: int = 56):
        super().__init__(parent)
        self.setText(icon_text)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self._size = size
        self._is_active = False
        self._init_style()

    def set_active(self, active: bool):
        self._is_active = active
        self._init_style()

    def _init_style(self):
        active_style = "background-color: #5A7FFF; color: white; border: 2px solid #5A7FFF;" if self._is_active else ""
        inactive_style = "background-color: #FFFFFF; color: #333333; border: 2px solid #E0E0E0;"
        self.setStyleSheet(f"""
            QPushButton {{ {active_style if self._is_active else inactive_style}
                border-radius: {self._size // 2}px; font-size: 20px; font-weight: bold; }}
            QPushButton:hover {{ background-color: #F0F4FF; border: 2px solid #5A7FFF; }}
        """)

class ColorSwatchButton(ToolButton):
    def __init__(self, color_hex: str, tooltip: str = "", size: int = 44, parent=None):
        self._color_hex = color_hex
        super().__init__(tooltip=tooltip or color_hex, icon_text="", parent=parent, size=size)
        self._is_selected = False
        self._init_style()

    @property
    def color_hex(self): return self._color_hex

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._init_style()
        
    def _init_style(self):
        border = "3px solid #5A7FFF" if getattr(self, '_is_selected', False) else "2px solid #FFFFFF"
        self.setStyleSheet(f"QPushButton {{ background-color: {self._color_hex}; border: {border}; border-radius: {self._size // 2}px; }}")

class SizeButton(ToolButton):
    def __init__(self, label: str, value: int, parent=None):
        """
        label: Текст на кнопке (S, M, L)
        value: Текущее значение в пикселях
        """
        super().__init__(tooltip=f"Размер: {value}px", icon_text=label, parent=parent, size=60)
        self.value = value
        self.setStyleSheet("font-size: 14px; font-weight: bold;")

    def update_value(self, new_value: int):
        self.value = new_value
        self.setToolTip(f"Размер: {new_value}px")
        # Перерисовка не нужна, текст (S/M/L) остается тем же

class GestureHintWidget(QLabel):
    def __init__(self):
        super().__init__("Ожидание руки...")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: #2C3E50; color: #ECF0F1; padding: 10px 20px; border-radius: 10px; font-weight: 600;")
        self.setFixedHeight(40)
    
    def update_hint(self, gesture: str):
        mapping = {
            "idle": "✋ Поднимите палец для рисования",
            "drawing": "☝️ Рисование (Указательный палец)",
            "erasing": "🖐 Ластик (Раскрытая ладонь)",
        }
        text = mapping.get(gesture, "👀 Поиск руки...")
        self.setText(text)
        
        if gesture == "drawing":
            self.setStyleSheet("background: #27AE60; color: white; padding: 10px 20px; border-radius: 10px; font-weight: bold;")
        elif gesture == "erasing":
            self.setStyleSheet("background: #E67E22; color: white; padding: 10px 20px; border-radius: 10px; font-weight: bold;")
        else:
            self.setStyleSheet("background: #2C3E50; color: #ECF0F1; padding: 10px 20px; border-radius: 10px;")

class SettingsDialog(QDialog):
    def __init__(self, model: CanvasModel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки холста")
        self.model = model
        self.resize(300, 200)
        layout = QVBoxLayout(self)
        self.grid_check = QCheckBox("Показывать сетку")
        self.grid_check.setChecked(model.show_grid)
        layout.addWidget(self.grid_check)
        layout.addWidget(QLabel("Размер сетки:"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(20, 200)
        self.slider.setValue(model.grid_step)
        layout.addWidget(self.slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def accept(self):
        self.model.show_grid = self.grid_check.isChecked()
        self.model.grid_step = self.slider.value()
        super().accept()

class MainWindow(QMainWindow):
    def __init__(self, model: CanvasModel, engine: RenderEngine):
        super().__init__()
        self._model = model
        self._engine = engine
        
        self._tool_buttons: Dict[str, ToolButton] = {}
        self._color_swatches: List[ColorSwatchButton] = []
        self._size_buttons: List[SizeButton] = []
        
        self._init_ui()
        self.update_ui_state()

    def _init_ui(self):
        self.setWindowTitle("Intelligent Canvas")
        self.resize(1400, 900)
        self.setStyleSheet("QMainWindow { background-color: #E9EEF3; }")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self._create_top_palette_bar(main_layout)
        
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(12)
        self._create_left_toolbar(mid_layout)
        
        self.canvas_widget = CanvasWidget(self._model, self._engine)
        mid_layout.addWidget(self.canvas_widget, stretch=1)
        
        self._create_right_control_panel(mid_layout)
        main_layout.addLayout(mid_layout, stretch=1)
        
        self._create_bottom_bar(main_layout)

    def _create_top_palette_bar(self, layout):
        frame = QFrame()
        frame.setFixedHeight(96)
        frame.setStyleSheet("QFrame { background: #2C3E50; border-radius: 8px; }")
        l = QHBoxLayout(frame)
        l.setContentsMargins(18, 12, 18, 12)
        
        self._active_mode_label = QLabel("🖌 Brush")
        self._active_mode_label.setStyleSheet("color: #ECF0F1; font-weight: 700; font-size: 16px;")
        l.addWidget(self._active_mode_label)
        
        swatch_container = QWidget()
        sl = QHBoxLayout(swatch_container)
        colors = ["#FF4757", "#FF7A3D", "#FFC312", "#2ECC71", "#3498DB", "#9B59B6", "#E91E63", "#2C3E50", "#FFFFFF"]
        for c in colors:
            btn = ColorSwatchButton(c)
            btn.clicked.connect(lambda ch, col=c, b=btn: self.set_color(col, b))
            sl.addWidget(btn)
            self._color_swatches.append(btn)
        l.addWidget(swatch_container, stretch=1)
        layout.addWidget(frame)

    def _create_left_toolbar(self, layout):
        frame = QFrame()
        frame.setFixedWidth(92)
        frame.setStyleSheet("background: transparent;")
        l = QVBoxLayout(frame)
        
        for tool_id, icon, tip in [("Brush", "🖌", "Кисть"), ("Eraser", "🧽", "Ластик")]:
            btn = ToolButton(tip, icon, size=56)
            btn.clicked.connect(lambda ch, t=tool_id: self.set_tool(t))
            l.addWidget(btn)
            self._tool_buttons[tool_id] = btn
        
        l.addStretch()
        layout.addWidget(frame)

    def _create_right_control_panel(self, layout):
        frame = QFrame()
        frame.setFixedWidth(96)
        frame.setStyleSheet("background: transparent;")
        l = QVBoxLayout(frame)
        
        actions = [
            ("Save", "💾", self._on_save),
            ("Open", "📁", self._on_open),
            ("Undo", "↶", lambda: (self._model.undo(), self.canvas_widget.update())),
            ("Redo", "↷", lambda: (self._model.redo(), self.canvas_widget.update())),
            ("Clear", "🗑", lambda: (self._model.clear(), self.canvas_widget.update()))
        ]
        for name, icon, func in actions:
            btn = ToolButton(name, icon, size=56)
            btn.clicked.connect(func)
            l.addWidget(btn)
        l.addStretch()
        settings_btn = ToolButton("Настройки", "⚙", size=56)
        settings_btn.clicked.connect(self._on_settings)
        l.addWidget(settings_btn)
        layout.addWidget(frame)

    def _create_bottom_bar(self, layout):
        frame = QFrame()
        frame.setFixedHeight(110)
        frame.setStyleSheet("background: #FFFFFF; border: 2px solid #E0E0E0; border-radius: 8px;")
        l = QHBoxLayout(frame)
        
        self.gesture_hint = GestureHintWidget()
        l.addWidget(self.gesture_hint)
        l.addStretch()
        
        l.addWidget(QLabel("Размер:"))
        # Кнопки S, M, L, XL. Значения будут меняться динамически.
        labels = ["S", "M", "L", "XL"]
        default_vals = [4, 8, 16, 24]
        
        for label, val in zip(labels, default_vals):
            btn = SizeButton(label, val)
            btn.clicked.connect(lambda ch, b=btn: self.set_size(b))
            l.addWidget(btn)
            self._size_buttons.append(btn)
            
        layout.addWidget(frame)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
    
    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить изображение", "", "PNG Files (*.png)")
        if path:
            self._engine.save_to_file(path)

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть фон", "", "Images (*.png *.jpg)")
        if path:
            self._model.load_background(path)
            self.canvas_widget.update()

    def _on_settings(self):
        dlg = SettingsDialog(self._model, self)
        if dlg.exec():
            self.canvas_widget.update()

    def set_color(self, hex_color, btn_obj):
        self._model.set_color(QColor(hex_color))
        for b in self._color_swatches:
            b.set_selected(b is btn_obj)
        self.status_bar.showMessage(f"Цвет: {hex_color}")

    def set_tool(self, tool_id):
        # 1. Устанавливаем инструмент в модели
        self._model.set_tool(tool_id.lower())
        
        # 2. Обновляем UI кнопок инструментов
        self._active_mode_label.setText(f"{self._tool_buttons[tool_id].text()} {tool_id}")
        for t, b in self._tool_buttons.items():
            b.set_active(t == tool_id)
            
        # 3. Обновляем значения кнопок размеров под инструмент
        self._update_size_buttons_for_tool(tool_id)
        
        self.status_bar.showMessage(f"Инструмент: {tool_id}")

    def _update_size_buttons_for_tool(self, tool_id):
        # Определяем набор размеров
        if tool_id == "Brush":
            sizes = [4, 8, 16, 24]
        else: # Eraser
            sizes = [30, 60, 90, 120]
            
        current_size = self._model.current_thickness
        
        # Обновляем кнопки и ищем активную
        closest_btn = None
        min_diff = float('inf')
        
        for btn, size_val in zip(self._size_buttons, sizes):
            btn.update_value(size_val)
            
            # Проверяем, совпадает ли с текущим
            diff = abs(current_size - size_val)
            if diff < min_diff:
                min_diff = diff
                closest_btn = btn
        
        # Подсвечиваем активный размер
        for btn in self._size_buttons:
            btn.set_active(btn is closest_btn)

    def set_size(self, btn_obj: SizeButton):
        self._model.set_thickness(btn_obj.value)
        for b in self._size_buttons:
            b.set_active(b is btn_obj)

    def update_ui_state(self):
        self.set_tool("Brush")
        if self._color_swatches:
            self.set_color(self._color_swatches[4].color_hex, self._color_swatches[4])
            
    def update_fps(self, fps: float):
        # Удалено по требованию
        pass

    def update_gesture_hint(self, gesture: str):
        self.gesture_hint.update_hint(gesture)