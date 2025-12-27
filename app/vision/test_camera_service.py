# test_camera_service.py

import time
import cv2
from app.vision import CameraService
from app.vision.frame_data import FrameData
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_drawing

# === НАСТРОЙКИ ТЕСТОВОГО СКРИПТА ===
MIRROR_VIDEO = True     # ← зеркалировать поток

def main():
    SHOW_SKELETON = True    # ← включить/выключить отображение костей

    print("🚀 Starting test of CameraService with visualization...")
    print(f"🔧 Settings: mirror = {MIRROR_VIDEO}, skeleton = {SHOW_SKELETON}")

    camera = CameraService(camera_index=0, mirror=MIRROR_VIDEO)


    print("\n🎥 Starting video capture...")
    frame_count = 0
    start_time = time.perf_counter()

    cv2.namedWindow('Smart Canvas - Gesture Feed', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Smart Canvas - Gesture Feed', 800, 600)

    try:
        while True:
            frame_data: FrameData = camera.get_frame_data()

            if frame_data.raw_frame is None:
                print("🔴 Camera is not responding...")
                time.sleep(1)
                continue

            frame_count += 1
            display_frame = frame_data.raw_frame.copy()

            # === 1. Отрисовка скелета (если включено) ===
            if SHOW_SKELETON:
                # Для этого нам нужны landmarks — добавим их в CameraService или получим отдельно
                # Но проще: если вы хотите скелет — временно запустим MediaPipe внутри теста
                # (в продакшене это не нужно, но для отладки — ок)

                # ⚠️ ВАЖНО: это дублирует обработку! В реальном приложении передавайте landmarks из CameraService!
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                hands = mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=2,
                    min_detection_confidence=0.7,
                    min_tracking_confidence=0.5
                )
                results = hands.process(rgb_frame)
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(
                            display_frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                            mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                        )
                hands.close()

            # === 2. Точка указательного пальца ===
            if frame_data.index_finger_x != -1 and frame_data.index_finger_y != -1:
                cv2.circle(display_frame, (frame_data.index_finger_x, frame_data.index_finger_y), 10, (0, 255, 255), -1)
                    # Отображаем координаты рядом с точкой
                coord_text = f"({frame_data.index_finger_x}, {frame_data.index_finger_y})"
                cv2.putText(
                    display_frame,
                    coord_text,
                    (frame_data.index_finger_x + 15, frame_data.index_finger_y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )
            

            # === 3. Текстовая информация ===
            info_lines = [
                f"Gesture: {frame_data.gesture}",
                f"FPS: {frame_data.fps:.1f}",
                f"Latency: {frame_data.latency_ms:.1f} ms",
            ]
            if SHOW_SKELETON:
                info_lines.append("Skeleton: ON")
            if MIRROR_VIDEO:
                info_lines.append("Mirror: ON")

            y_offset = 30
            for line in info_lines:
                cv2.putText(display_frame, line, (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_offset += 25

            cv2.imshow('Smart Canvas - Gesture Feed', display_frame)

            # === 4. Управление ===
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Переключение скелета по нажатию 's'
                # global SHOW_SKELETON
                SHOW_SKELETON = not SHOW_SKELETON
                print(f"Skeleton: {'ON' if SHOW_SKELETON else 'OFF'}")

            # === 5. Консольный вывод (опционально) ===
            if frame_count % 10 == 0:
                print(f"FPS: {frame_data.fps:.1f} | Gesture: {frame_data.gesture}")

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")

    finally:
        camera.release()
        cv2.destroyAllWindows()
        elapsed = time.perf_counter() - start_time
        print(f"\n📊 Summary: {frame_count} frames in {elapsed:.1f} sec ({frame_count / elapsed:.1f} FPS)")

if __name__ == "__main__":
    main()