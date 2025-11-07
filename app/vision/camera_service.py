# app/vision/camera_service.py
import time
from .frame_data import FrameData
from .gesture_detector import GestureDetector
from .smoother import OneEuroFilter
from .metrics import MetricsCollector

import cv2
import mediapipe as mp
import numpy as np

class CameraService:
    def __init__(self, camera_index: int = 0, resolution: tuple = (640, 480)):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Не удалось открыть камеру {camera_index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        # MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )

        # Внутренние компоненты
        self.gesture_detector = GestureDetector()
        self.smoother = OneEuroFilter()
        self.metrics = MetricsCollector()

        # Состояние
        self.last_frame_time = 0
        self.frame_count = 0

    def start(self):
        """Запуск захвата — можно вызвать после инициализации."""
        pass  # если нужно, добавьте логику

    def get_frame_data(self) -> FrameData:
        """
        Главный метод — возвращает данные текущего кадра.
        Другие модули используют ТОЛЬКО этот метод.
        """
        frame_data = FrameData()

        # Измеряем задержку
        current_time = time.perf_counter()
        frame_data.latency_ms = (current_time - self.last_frame_time) * 1000
        self.last_frame_time = current_time

        # Получаем кадр
        ret, frame = self.cap.read()
        if not ret:
            frame_data.raw_frame = None
            return frame_data

        frame_data.raw_frame = frame.copy()  # для отображения

        # Обработка через MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        # Сбор метрик
        frame_data.detection_confidence = getattr(results, 'multi_hand_landmarks', []) and 0.7 or 0.0
        frame_data.tracking_confidence = 0.5  # можно уточнить
        frame_data.num_hands_detected = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0

        # Обработка жестов и сглаживание
        if results.multi_hand_landmarks:
            # Применяем сглаживание
            smoothed_landmarks = []
            for landmarks in results.multi_hand_landmarks:
                smoothed = self.smoother.smooth_landmarks(landmarks.landmark)
                smoothed_landmarks.append(smoothed)

            # Детекция жестов
            gesture_result = self.gesture_detector.detect(
                smoothed_landmarks, results.multi_handedness
            )

            frame_data.gesture = gesture_result.gesture
            frame_data.is_pinch_active = gesture_result.is_pinch_active
            frame_data.is_palm_open = gesture_result.is_palm_open
            frame_data.index_finger_x = gesture_result.index_finger_x
            frame_data.index_finger_y = gesture_result.index_finger_y
            frame_data.scale_factor = gesture_result.scale_factor
            frame_data.hands_distance_px = gesture_result.hands_distance_px

        # Обновляем FPS
        self.frame_count += 1
        if self.frame_count % 30 == 0:  # каждые 30 кадров
            frame_data.fps = self.metrics.calculate_fps()

        return frame_data
    
    # В CameraService

    def list_devices(self) -> list:
        """Возвращает список доступных камер."""
        devices = []
        for i in range(10):  # проверяем первые 10 устройств
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                devices.append(i)
                cap.release()
        return devices

    def set_camera_device(self, index: int):
        """Переключиться на другое устройство."""
        self.release()
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            raise RuntimeError(f"❌ Не удалось переключиться на камеру {index}")

    def release(self):
        if self.cap.isOpened():
            self.cap.release()

    def __del__(self):
        self.release()