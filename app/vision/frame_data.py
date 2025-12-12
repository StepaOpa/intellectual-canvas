from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class FrameData:
    # Входной кадр (BGR, numpy array)
    raw_frame: Optional[np.ndarray] = None

    # Основные данные для холста
    gesture: str = "idle"          # "drawing", "erasing", "idle"
    
    # Координаты курсора (X, Y) в пикселях камеры
    # Для рисования — кончик указательного пальца
    # Для ластика — центр ладони
    cursor_x: int = -1       
    cursor_y: int = -1

    # Метрики качества
    fps: float = 0.0
    latency_ms: float = 0.0
    
    # Служебные флаги
    is_tracking: bool = False      # Захвачена ли рука системой