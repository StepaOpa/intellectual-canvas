import time
import cv2
import mediapipe as mp
import numpy as np

from .frame_data import FrameData
from .gesture_detector import GestureDetector
from .smoother import OneEuroFilter
from .metrics import MetricsCollector

class CameraService:
    def __init__(self, camera_index: int = 0, resolution: tuple = (640, 480)):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Не удалось открыть камеру {camera_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        
        # Размеры кадра
        self.width = resolution[0]
        self.height = resolution[1]

        # MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,     # Видим две, но обрабатываем одну (активную)
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        )

        # Компоненты
        self.detector = GestureDetector()
        self.smoother = OneEuroFilter(min_cutoff=0.5, beta=0.2) # Тюнинг: beta повыше для реакции
        self.metrics = MetricsCollector()

        # Состояние трекинга (Hand Locking)
        # Мы запоминаем позицию запястья активной руки, чтобы в следующем кадре найти именно её
        self.active_hand_prev_wrist = None 
        self.max_lost_frames = 15  # Сколько кадров помнить руку, если она пропала
        self.lost_frame_count = 0

        self.last_frame_time = 0

    def get_frame_data(self) -> FrameData:
        frame_data = FrameData()
        
        # 1. Захват кадра
        current_time = time.perf_counter()
        frame_data.latency_ms = (current_time - self.last_frame_time) * 1000
        self.last_frame_time = current_time

        ret, frame = self.cap.read()
        if not ret:
            frame_data.raw_frame = None
            return frame_data

        frame_data.raw_frame = frame.copy()
        
        # 2. Обработка MP
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        target_landmarks = None

        if results.multi_hand_landmarks:
            # --- ЛОГИКА ВЫБОРА РУКИ (Hand Locking) ---
            all_hands = results.multi_hand_landmarks
            
            if self.active_hand_prev_wrist is None:
                # Если рука не захвачена, берем ту, что ближе к центру экрана
                target_landmarks = self._find_center_hand(all_hands)
            else:
                # Если рука была захвачена, ищем ту, запястье которой ближе всего к предыдущей позиции
                target_landmarks = self._find_closest_hand(all_hands, self.active_hand_prev_wrist)
                
                # Если самая близкая рука слишком далеко (скачок), значит мы потеряли трекинг
                if target_landmarks:
                    wrist = target_landmarks.landmark[0]
                    dist = np.hypot(wrist.x - self.active_hand_prev_wrist[0], 
                                    wrist.y - self.active_hand_prev_wrist[1])
                    if dist > 0.3: # Порог скачка (30% экрана)
                        target_landmarks = None # Сброс, это не та рука

            if target_landmarks:
                # Обновляем трекинг
                self.active_hand_prev_wrist = (target_landmarks.landmark[0].x, target_landmarks.landmark[0].y)
                self.lost_frame_count = 0
                frame_data.is_tracking = True
            else:
                # Рука потеряна в этом кадре
                self.lost_frame_count += 1
                if self.lost_frame_count > self.max_lost_frames:
                    self.active_hand_prev_wrist = None # Полный сброс
                    self.smoother.reset() # Сбрасываем фильтр сглаживания
                
        else:
            self.lost_frame_count += 1
            if self.lost_frame_count > self.max_lost_frames:
                self.active_hand_prev_wrist = None
                self.smoother.reset()

        # 3. Распознавание жестов (только для целевой руки)
        if target_landmarks:
            gesture_res = self.detector.detect(target_landmarks.landmark, self.width, self.height)
            
            frame_data.gesture = gesture_res.gesture
            
            if gesture_res.gesture != "idle" and gesture_res.x != -1:
                # Сглаживаем координаты
                sx, sy = self.smoother.smooth_point(gesture_res.x, gesture_res.y)
                frame_data.cursor_x = int(sx)
                frame_data.cursor_y = int(sy)
            else:
                # Если idle, сбрасываем сглаживатель, чтобы не было "шлейфа" при начале нового штриха
                self.smoother.reset()

        # 4. FPS
        frame_data.fps = self.metrics.calculate_fps()

        return frame_data

    def _find_center_hand(self, hands_list):
        """Находит руку, запястье которой ближе всего к центру кадра (0.5, 0.5)"""
        best_hand = None
        min_dist = float('inf')
        
        for hand in hands_list:
            wrist = hand.landmark[0]
            dist = np.hypot(wrist.x - 0.5, wrist.y - 0.5)
            if dist < min_dist:
                min_dist = dist
                best_hand = hand
        return best_hand

    def _find_closest_hand(self, hands_list, prev_wrist_coords):
        """Находит руку, ближайшую к предыдущим координатам"""
        best_hand = None
        min_dist = float('inf')
        px, py = prev_wrist_coords
        
        for hand in hands_list:
            wrist = hand.landmark[0]
            dist = np.hypot(wrist.x - px, wrist.y - py)
            if dist < min_dist:
                min_dist = dist
                best_hand = hand
        return best_hand

    def release(self):
        if self.cap.isOpened():
            self.cap.release()