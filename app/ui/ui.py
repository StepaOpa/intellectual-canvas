from typing import Optional, Dict, List
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QPaintEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy, QStatusBar,
    QFileDialog, QDialog, QCheckBox, QSlider, QDialogButtonBox, QMessageBox
)

from app.canvas.canvas import CanvasModel, RenderEngine

# --- ВИДЖЕТ ХОЛСТА (Без изменений) ---
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

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        scale_factor = 1.1 if delta > 0 else 0.9
        mouse_pos = event.position() 
        self._engine.zoom(scale_factor, mouse_pos)
        self.update()

    def _draw_grid(self, painter: QPainter):
        step = self._model.grid_step * self._engine.scale_factor
        if step < 20: return 
        painter.save()
        painter.translate(self._engine.offset)
        painter.scale(self._engine.scale_factor, self._engine.scale_factor)
        pen = QPen(QColor(0, 0, 0, 15))
        pen.setWidthF(1.0 / self._engine.scale_factor) 
        painter.setPen(pen)
        w, h = self._model.width, self._model.height
        for x in range(0, w, self._model.grid_step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, self._model.grid_step):
            painter.drawLine(0, y, w, y)
        painter.restore()

    def mousePressEvent(self, event: QMouseEvent): pass 
    def mouseMoveEvent(self, event: QMouseEvent): pass
    def mouseReleaseEvent(self, event: QMouseEvent): pass

# --- УЛУЧШЕННЫЕ КНОПКИ ---
class ToolButton(QPushButton):
    def __init__(self, tooltip: str, icon_text: str, parent=None, size: int = 56, checkable=False):
        super().__init__(parent)
        self.setText(icon_text)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self._size = size
        self._is_active = False
        self.setCheckable(checkable)
        self._init_style()

    def set_active(self, active: bool):
        self._is_active = active
        self._init_style()
        
    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._init_style()

    def _init_style(self):
        is_pushed = self.isChecked() or self._is_active
        
        # Определение цветов для разных состояний
        # Обычная кнопка (Инструмент)
        bg_normal = "#FFFFFF"
        bg_normal_hover = "#F5F6FA"
        border_normal = "#E0E0E0"
        text_normal = "#333333"

        bg_active = "#5A7FFF"
        bg_active_hover = "#7A9FFF"
        border_active = "#5A7FFF"
        text_active = "white"

        # Кнопка-переключатель (Жесты)
        # Зеленый (ВКЛ)
        bg_on = "#2ECC71"
        bg_on_hover = "#4CD988"
        border_on = "#27AE60"
        
        # Красный (ВЫКЛ)
        bg_off = "#FF7675"
        bg_off_hover = "#FF9F9E"
        border_off = "#D63031"

        # Формируем стиль
        style = ""
        
        if self.isCheckable():
            if self.isChecked():
                # ВКЛЮЧЕНО (Зеленый стиль)
                style = f"""
                    QPushButton {{
                        background-color: {bg_on}; color: white; border: 2px solid {border_on};
                        border-radius: {self._size // 2}px; font-size: 16px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: {bg_on_hover}; }}
                """
            else:
                # ВЫКЛЮЧЕНО (Красный стиль)
                style = f"""
                    QPushButton {{
                        background-color: {bg_off}; color: white; border: 2px solid {border_off};
                        border-radius: {self._size // 2}px; font-size: 16px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: {bg_off_hover}; }}
                """
        else:
            # Обычные инструменты
            if is_pushed:
                # Активный инструмент (Синий)
                style = f"""
                    QPushButton {{
                        background-color: {bg_active}; color: {text_active}; border: 3px solid {border_active};
                        border-radius: {self._size // 2}px; font-size: 24px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: {bg_active_hover}; }}
                """
            else:
                # Неактивный инструмент (Белый)
                style = f"""
                    QPushButton {{
                        background-color: {bg_normal}; color: {text_normal}; border: 2px solid {border_normal};
                        border-radius: {self._size // 2}px; font-size: 24px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: {bg_normal_hover}; border: 2px solid #BDC3C7; }}
                """

        self.setStyleSheet(style)

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
        # Для цвета hover сделаем просто чуть светлее границы
        border = "3px solid #5A7FFF" if getattr(self, '_is_selected', False) else "2px solid #FFFFFF"
        self.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {self._color_hex}; 
                border: {border}; 
                border-radius: {self._size // 2}px; 
            }}
            QPushButton:hover {{ border: 3px solid #BDC3C7; }}
        """)

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

# --- MAIN WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self, model: CanvasModel, engine: RenderEngine):
        super().__init__()
        self._model = model
        self._engine = engine
        
        self._tool_buttons: Dict[str, ToolButton] = {}
        self._color_swatches: List[ColorSwatchButton] = []
        
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
        frame.setStyleSheet("QFrame { background: #2C3E50; border-radius: 16px; }")
        l = QHBoxLayout(frame)
        l.setContentsMargins(24, 12, 24, 12)
        
        self._active_mode_label = QLabel("🖌 Brush")
        self._active_mode_label.setStyleSheet("color: #ECF0F1; font-weight: 700; font-size: 20px; margin-right: 20px;")
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
        frame.setFixedWidth(100)
        frame.setStyleSheet("background: transparent;")
        l = QVBoxLayout(frame)
        l.setSpacing(15)
        
        # Инструменты
        for tool_id, icon, tip in [("Brush", "🖌", "Кисть"), ("Eraser", "🧽", "Ластик")]:
            btn = ToolButton(tip, icon, size=64) # Чуть больше размер
            btn.clicked.connect(lambda ch, t=tool_id: self.set_tool(t))
            l.addWidget(btn)
            self._tool_buttons[tool_id] = btn
        
        l.addStretch()
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #BDC3C7;")
        l.addWidget(line)
        l.addSpacing(10)

        # КНОПКИ ЖЕСТОВ
        # Рисование
        self.btn_toggle_draw = ToolButton("Управление жестом рисования", "☝️", size=64, checkable=True)
        self.btn_toggle_draw.setChecked(True)
        self.btn_toggle_draw.setText("ВКЛ")
        self.btn_toggle_draw.clicked.connect(self._update_gesture_toggles)
        l.addWidget(self.btn_toggle_draw)
        
        l.addSpacing(5)

        # Ластик
        self.btn_toggle_erase = ToolButton("Управление жестом ластика", "🖐", size=64, checkable=True)
        self.btn_toggle_erase.setChecked(True)
        self.btn_toggle_erase.setText("ВКЛ")
        self.btn_toggle_erase.clicked.connect(self._update_gesture_toggles)
        l.addWidget(self.btn_toggle_erase)
        
        layout.addWidget(frame)

    def _create_right_control_panel(self, layout):
        frame = QFrame()
        frame.setFixedWidth(96)
        frame.setStyleSheet("background: transparent;")
        l = QVBoxLayout(frame)
        l.setSpacing(15)
        
        actions = [
            ("Save", "💾", self._on_save),
            ("Open", "📁", self._on_open),
            ("Undo", "↶", lambda: (self._model.undo(), self.canvas_widget.update())),
            ("Redo", "↷", lambda: (self._model.redo(), self.canvas_widget.update())),
            ("Clear", "🗑", lambda: (self._model.clear(), self.canvas_widget.update()))
        ]
        for name, icon, func in actions:
            btn = ToolButton(name, icon, size=60)
            btn.clicked.connect(func)
            l.addWidget(btn)
        l.addStretch()
        layout.addWidget(frame)

    def _create_bottom_bar(self, layout):
        frame = QFrame()
        frame.setFixedHeight(120)
        # Белый фон, тень через border (имитация)
        frame.setStyleSheet("background: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 16px;")
        l = QHBoxLayout(frame)
        l.setSpacing(30)
        l.setContentsMargins(30, 15, 30, 15)
        
        # Жестовая подсказка
        self.gesture_hint = GestureHintWidget()
        self.gesture_hint.setFixedWidth(280)
        l.addWidget(self.gesture_hint)
        
        # Вертикальный разделитель
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #ECF0F1;")
        l.addWidget(sep1)
        
        l.addStretch()
        
        # --- СЛАЙДЕРЫ ---
        # 1. Слайдер Кисти
        brush_layout = self._create_slider_control("РАЗМЕР КИСТИ", 2, 50, self._model.brush_size, 
                                                   self._on_brush_size_change, color="#2980B9")
        l.addLayout(brush_layout)

        l.addSpacing(20)

        # 2. Слайдер Ластика
        eraser_layout = self._create_slider_control("РАЗМЕР ЛАСТИКА", 10, 200, self._model.eraser_size,
                                                    self._on_eraser_size_change, color="#8E44AD")
        l.addLayout(eraser_layout)

        l.addStretch()
        
        layout.addWidget(frame)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
    
    def _create_slider_control(self, label_text, min_val, max_val, init_val, callback, color="#333"):
        container = QVBoxLayout()
        container.setSpacing(8)
        container.setAlignment(Qt.AlignCenter)
        
        # Метка названия
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color}; letter-spacing: 1px;")
        
        # Значение
        value_label = QLabel(f"{int(init_val)} px")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #2C3E50;")
        
        # Слайдер
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(int(init_val))
        slider.setFixedWidth(200)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid #bbb;
                background: white;
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::sub-page:horizontal {{
                background: {color};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: white;
                border: 2px solid {color};
                width: 18px;
                height: 18px;
                margin: -6px 0; 
                border-radius: 9px;
            }}
        """)
        
        slider.valueChanged.connect(lambda v: (value_label.setText(f"{v} px"), callback(v)))
        
        container.addWidget(label)
        container.addWidget(value_label)
        container.addWidget(slider)
        
        return container

    def _update_gesture_toggles(self):
        self._model.allow_drawing = self.btn_toggle_draw.isChecked()
        self._model.allow_erasing = self.btn_toggle_erase.isChecked()
        
        # Обновляем текст и стиль
        # Текст ВКЛ / ВЫКЛ с иконкой
        self.btn_toggle_draw.setText("☝️\nВКЛ" if self.btn_toggle_draw.isChecked() else "☝️\nВЫКЛ")
        self.btn_toggle_draw._init_style()
        
        self.btn_toggle_erase.setText("🖐\nВКЛ" if self.btn_toggle_erase.isChecked() else "🖐\nВЫКЛ")
        self.btn_toggle_erase._init_style()

    def _on_brush_size_change(self, val):
        self._model.set_brush_size(val)

    def _on_eraser_size_change(self, val):
        self._model.set_eraser_size(val)

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить изображение", "", "PNG Files (*.png)")
        if path:
            self._engine.save_to_file(path)

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть фон", "", "Images (*.png *.jpg)")
        if path:
            self._model.load_background(path)
            self.canvas_widget.update()

    def set_color(self, hex_color, btn_obj):
        self._model.set_color(QColor(hex_color))
        for b in self._color_swatches:
            b.set_selected(b is btn_obj)
        self.status_bar.showMessage(f"Цвет: {hex_color}")

    def set_tool(self, tool_id):
        self._model.set_tool(tool_id.lower())
        self._active_mode_label.setText(f"{self._tool_buttons[tool_id].text()} {tool_id}")
        for t, b in self._tool_buttons.items():
            b.set_active(t == tool_id)
        self.status_bar.showMessage(f"Инструмент: {tool_id}")

    def update_ui_state(self):
        self.set_tool("Brush")
        if self._color_swatches:
            self.set_color(self._color_swatches[4].color_hex, self._color_swatches[4])
        self._update_gesture_toggles()
            
    def update_gesture_hint(self, gesture: str):
        self.gesture_hint.update_hint(gesture)