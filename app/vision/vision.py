# app/vision/video_capture.py

import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, List


class CameraService:
    def __init__(self, camera_index: int = 0, resolution: Tuple[int, int] = (640, 480)):
        """
        Инициализация сервиса захвата видео.
        :param camera_index: индекс камеры (по умолчанию 0 — основная камера)
        """
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Не удалось открыть камеру {camera_index}")

        # Настройка разрешения (опционально)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        # Инициализация MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Получить один кадр с камеры.
        :return: кадр (BGR), или None, если кадр не получен
        """
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[dict]]:
        """
        Обработать кадр: обнаружить руки и вернуть ключевые точки.
        :param frame: входной кадр (BGR)
        :return: (обработанный кадр, список словарей с landmarks)
        """
        # Конвертируем в RGB для MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Обработка кадра
        results = self.hands.process(rgb_frame)

        # Рисуем руки на кадре (опционально — для отладки)
        annotated_frame = frame.copy()
        hand_landmarks_list = []

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Рисуем ключевые точки и соединения
                self.mp_drawing.draw_landmarks(
                    annotated_frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )

                # Сохраняем координаты ключевых точек
                landmarks = []
                for i, landmark in enumerate(hand_landmarks.landmark):
                    h, w, c = frame.shape
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    z = landmark.z  # относительная глубина
                    landmarks.append(
                        {
                            "id": i,
                            "x": x,
                            "y": y,
                            "z": z,
                            "visibility": landmark.visibility,
                        }
                    )
                hand_landmarks_list.append(
                    {
                        "landmarks": landmarks,
                        "handedness": (
                            results.multi_handedness[0].classification[0].label
                            if hasattr(results.multi_handedness[0], "classification")
                            else "Unknown"
                        ),
                    }
                )

        return annotated_frame, hand_landmarks_list

    def release(self):
        """Освободить камеру."""
        if self.cap.isOpened():
            self.cap.release()

    def __del__(self):
        self.release()
