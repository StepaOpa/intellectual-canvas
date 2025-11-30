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
        self.buffer_size = 4 # Чуть увеличили для надежности
        
    def detect(self, landmarks, img_width, img_height) -> GestureResult:
        result = GestureResult()
        
        if not landmarks:
            return result

        # 1. Анализ пальцев
        # fingers_state: [Thumb, Index, Middle, Ring, Pinky] (True = Выпрямлен, False = Сжат)
        fingers_extended = self._check_fingers_extended(landmarks)
        
        current_gesture = "idle"
        
        # --- ЛОГИКА ЖЕСТОВ ---

        # ЛАСТИК: Все 5 пальцев выпрямлены (или хотя бы 4, кроме большого)
        # Иногда мизинец может быть чуть согнут, так что разрешаем 4 пальца
        if sum(fingers_extended) >= 4:
            current_gesture = "erasing"
            # Координаты: Центр ладони
            cx = (landmarks[0].x + landmarks[5].x + landmarks[17].x) / 3
            cy = (landmarks[0].y + landmarks[5].y + landmarks[17].y) / 3
            result.x = int(cx * img_width)
            result.y = int(cy * img_height)

        # РИСОВАНИЕ: Указательный палец выпрямлен.
        # Остальные (Средний, Безымянный, Мизинец) - СЖАТЫ.
        # Большой палец (index 0) - ИГНОРИРУЕМ (он может быть где угодно).
        elif fingers_extended[1] and not fingers_extended[2] and not fingers_extended[3] and not fingers_extended[4]:
            current_gesture = "drawing"
            # Координаты: Кончик указательного пальца
            result.x = int(landmarks[8].x * img_width)
            result.y = int(landmarks[8].y * img_height)

        else:
            current_gesture = "idle"

        # --- СТАБИЛИЗАЦИЯ (DEBOUNCING) ---
        self.gesture_buffer.append(current_gesture)
        if len(self.gesture_buffer) > self.buffer_size:
            self.gesture_buffer.pop(0)
            
        # Принимаем решение только если большинство кадров в буфере говорят одно и то же
        from collections import Counter
        most_common = Counter(self.gesture_buffer).most_common(1)[0]
        gesture_candidate, count = most_common
        
        # Порог уверенности:
        if count >= self.buffer_size - 1:
            result.gesture = gesture_candidate
        else:
            # Если нет консенсуса, оставляем последний подтвержденный или idle
            # (в данном случае просто вернем idle для безопасности, или последний результат из буфера)
            result.gesture = self.gesture_buffer[-1]

        # Если жест не определился как активный, координаты сбрасываем
        if result.gesture == "idle":
            result.x = -1
            result.y = -1
        # Если жест Drawing/Erasing, но буфер еще скачет, мы все равно можем вернуть координаты
        # из текущего кадра, если он совпадает с результирующим жестом
        elif result.gesture == current_gesture:
             pass # Координаты уже записаны выше
        else:
             # Если жест стабилизировался как Drawing, но в ТЕКУЩЕМ кадре сбой,
             # лучше не обновлять координаты (вернуть -1), чем дать ложные.
             # Но для плавности можно оставить старые. Здесь вернем текущие, если жест совпал.
             if result.gesture != current_gesture:
                 result.x = -1 # Прерывание
        
        return result

    def _check_fingers_extended(self, lm):
        """
        Возвращает список [Thumb, Index, Middle, Ring, Pinky].
        True — палец считается выпрямленным.
        """
        fingers = []
        wrist = lm[0]

        # 1. Thumb (Большой палец)
        # Сравниваем расстояние кончика до мизинца vs сустава до мизинца
        # Или просто вектор по X (для простоты используем упрощенную проверку)
        # Если кончик большого пальца дальше от основания мизинца (17), чем его сустав (2)
        fingers.append(self._dist(lm[4], lm[17]) > self._dist(lm[2], lm[17]))

        # 2. Остальные пальцы (Index, Middle, Ring, Pinky)
        # IDs: 8, 12, 16, 20
        # PIP joints (костяшки): 6, 10, 14, 18
        
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]

        for i, (tip_id, pip_id) in enumerate(zip(tips, pips)):
            # Базовая проверка: кончик дальше от запястья, чем сустав?
            d_tip = self._dist(lm[tip_id], wrist)
            d_pip = self._dist(lm[pip_id], wrist)
            
            is_extended = d_tip > d_pip * 1.1 # Множитель 1.1
            
            # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА ДЛЯ РИСОВАНИЯ (Средний, Безымянный, Мизинец)
            # Чтобы жест "Рисование" был стабильным, нам важно знать, что пальцы СЖАТЫ.
            # Если палец "полусогнут", мы хотим считать его СЖАТЫМ (False).
            # Поэтому для определения True (Выпрямлен) условия должны быть строгими.
            # А для False (Сжат) - легкими.
            
            # Если мы проверяем указательный (i==0 в этом цикле), он должен быть четко выпрямлен.
            # Если остальные (i>0), они должны быть четко НЕ выпрямлены.
            
            fingers.append(is_extended)

        return fingers

    def _dist(self, p1, p2):
        return np.hypot(p1.x - p2.x, p1.y - p2.y)