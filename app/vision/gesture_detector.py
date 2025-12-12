import numpy as np
from dataclasses import dataclass

@dataclass
class GestureResult:
    gesture: str = "idle"
    x: int = -1
    y: int = -1

class GestureDetector:
    def __init__(self):
        # Буфер для предотвращения мерцания жестов
        self.gesture_buffer = [] 
        self.buffer_size = 4
        
    def detect(self, landmarks, img_width, img_height) -> GestureResult:
        result = GestureResult()
        
        if not landmarks:
            return result

        # 1. Анализ пальцев
        # fingers_extended: [Thumb, Index, Middle, Ring, Pinky]
        fingers_extended = self._check_fingers_extended(landmarks)
        
        current_gesture = "idle"
        
        # --- ЛОГИКА ЖЕСТОВ ---

        # ЛАСТИК: Все 5 пальцев (или 4 без большого) выпрямлены
        if sum(fingers_extended) >= 4:
            current_gesture = "erasing"
            cx = (landmarks[0].x + landmarks[5].x + landmarks[17].x) / 3
            cy = (landmarks[0].y + landmarks[5].y + landmarks[17].y) / 3
            result.x = int(cx * img_width)
            result.y = int(cy * img_height)

        # РИСОВАНИЕ: Указательный выпрямлен, остальные сжаты.
        # Игнорируем большой палец (индекс 0).
        elif fingers_extended[1] and not fingers_extended[2] and not fingers_extended[3] and not fingers_extended[4]:
            current_gesture = "drawing"
            result.x = int(landmarks[8].x * img_width)
            result.y = int(landmarks[8].y * img_height)

        else:
            current_gesture = "idle"

        # --- СТАБИЛИЗАЦИЯ (DEBOUNCING) ---
        self.gesture_buffer.append(current_gesture)
        if len(self.gesture_buffer) > self.buffer_size:
            self.gesture_buffer.pop(0)
            
        from collections import Counter
        most_common = Counter(self.gesture_buffer).most_common(1)[0]
        gesture_candidate, count = most_common
        
        if count >= self.buffer_size - 1:
            result.gesture = gesture_candidate
        else:
            result.gesture = self.gesture_buffer[-1]

        if result.gesture == "idle":
            result.x = -1
            result.y = -1
        elif result.gesture != current_gesture:
             # Если буфер говорит "рисуем", а текущий кадр "сбой", держим координаты (или -1 для безопасности)
             result.x = -1
        
        return result

    def _check_fingers_extended(self, lm):
        """
        Возвращает список [Thumb, Index, Middle, Ring, Pinky].
        Учитывает 2D длину и 3D глубину (pointing at camera).
        """
        fingers = []
        wrist = lm[0]

        # 1. Thumb (Большой) - простая проверка
        fingers.append(self._dist(lm[4], lm[17]) > self._dist(lm[2], lm[17]))

        # 2. Остальные пальцы
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18] # Основания пальцев (Knuckles/PIP)

        for i, (tip_id, pip_id) in enumerate(zip(tips, pips)):
            # А. Проверка по 2D длине (стандартная)
            d_tip = self._dist(lm[tip_id], wrist)
            d_pip = self._dist(lm[pip_id], wrist)
            is_extended_2d = d_tip > d_pip * 1.1

            # Б. Проверка по 3D глубине (Z-координата)
            # MediaPipe Z: Отрицательное значение = ближе к камере.
            # Если кончик (Tip) существенно ближе сустава (PIP), значит палец смотрит в камеру.
            # Порог 0.04 подобран эмпирически (зависит от масштаба MP, но он нормализован).
            tip_z = lm[tip_id].z
            pip_z = lm[pip_id].z
            is_pointing_at_camera = (tip_z < pip_z - 0.04)

            # Палец считается выпрямленным, если он длинный ИЛИ смотрит в камеру
            fingers.append(is_extended_2d or is_pointing_at_camera)

        return fingers

    def _dist(self, p1, p2):
        return np.hypot(p1.x - p2.x, p1.y - p2.y)