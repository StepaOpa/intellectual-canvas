from dataclasses import dataclass
import numpy as np

@dataclass
class GestureResult:
    gesture: str = "idle"
    is_pinch_active: bool = False
    is_palm_open: bool = False
    index_finger_x: int = -1
    index_finger_y: int = -1
    scale_factor: float = 1.0
    hands_distance_px: float = 0.0

class GestureDetector:
    def detect(self, landmarks_list, handedness_list):
        result = GestureResult()

        if len(landmarks_list) == 0:
            return result

        # Работаем с первой рукой (можно настроить)
        hand_landmarks = landmarks_list[0]
        h, w, _ = 480, 640, 3  # примерное разрешение

        # Координаты указательного пальца (ID=8)
        index_finger = hand_landmarks[8]
        result.index_finger_x = int(index_finger.x * w)
        result.index_finger_y = int(index_finger.y * h)

        # Детекция pinch (большой + указательный палец сближены)
        thumb = hand_landmarks[4]
        distance = np.sqrt((index_finger.x - thumb.x)**2 + (index_finger.y - thumb.y)**2)
        result.is_pinch_active = distance < 0.05  # порог — можно настраивать

        # Детекция раскрытой ладони (углы пальцев)
        # Упрощённо: если все пальцы разведены — ладонь открыта
        fingers_extended = [landmarks_list[0][i] for i in [8, 12, 16, 20]]  # кончики пальцев
        palm_open = all([f.y < hand_landmarks[0].y for f in fingers_extended])  # упрощённая логика
        result.is_palm_open = palm_open

        # Двухруковое масштабирование
        if len(landmarks_list) >= 2:
            left_palm = np.array([landmarks_list[0][0].x, landmarks_list[0][0].y])  # запястье
            right_palm = np.array([landmarks_list[1][0].x, landmarks_list[1][0].y])
            distance = np.linalg.norm(left_palm - right_palm)
            result.hands_distance_px = distance * w  # в пикселях
            result.scale_factor = max(0.5, min(2.0, distance * 10))  # примерная логика

        # Определяем жест
        if result.is_pinch_active:
            result.gesture = "drawing"
        elif result.is_palm_open:
            result.gesture = "erasing"
        elif len(landmarks_list) >= 2:
            result.gesture = "scale"
        else:
            result.gesture = "idle"

        return result