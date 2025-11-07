from dataclasses import dataclass
from typing import Optional, List
import numpy as np

@dataclass
class FrameData:
    # Входной кадр (BGR, numpy array) — если нужно отобразить
    raw_frame: Optional[np.ndarray] = None

    # Основные данные для холста
    gesture: str = "idle"          # "drawing", "erasing", "scale", "menu", "idle"
    index_finger_x: int = -1       # координата указательного пальца
    index_finger_y: int = -1
    is_pinch_active: bool = False  # активен ли жест “pinch”
    is_palm_open: bool = False     # ладонь раскрыта (ластик)

    # Для двухрукового масштабирования
    scale_factor: float = 1.0      # 1.0 = без масштаба
    hands_distance_px: float = 0.0 # расстояние между центрами ладоней в пикселях

    # Метрики качества (для диагностики)
    fps: float = 0.0
    latency_ms: float = 0.0
    detection_confidence: float = 0.0
    tracking_confidence: float = 0.0
    num_hands_detected: int = 0

    # Дополнительно (по желанию)
    landmarks_left: Optional[List[dict]] = None   # ключевые точки левой руки
    landmarks_right: Optional[List[dict]] = None  # ключевые точки правой руки