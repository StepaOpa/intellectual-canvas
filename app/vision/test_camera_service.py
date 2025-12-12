# test_camera_service.py

import time
import cv2
from app.vision import CameraService
from app.vision.frame_data import FrameData

def main():
    print("🚀 Запуск тестирования CameraService с визуализацией...")

    # Попробуем найти доступные камеры
    camera = CameraService(camera_index=0)
    try:
        devices = camera.list_devices()
        print(f"✅ Доступные камеры: {devices}")
        if not devices:
            print("❌ Нет доступных камер. Проверьте подключение.")
            return
    except Exception as e:
        print(f"⚠️ Ошибка при поиске камер: {e}")

    # Запускаем сервис
    print("\n🎥 Начинаем захват видео...")
    frame_count = 0
    start_time = time.perf_counter()

    # Создаём окно
    cv2.namedWindow('Smart Canvas - Gesture Feed', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Smart Canvas - Gesture Feed', 800, 600)

    try:
        while True:
            frame_data: FrameData = camera.get_frame_data()

            if frame_data.raw_frame is None:
                print("🔴 Камера не отвечает. Перезапуск...")
                time.sleep(1)
                continue

            frame_count += 1

            # Копируем кадр для отрисовки
            display_frame = frame_data.raw_frame.copy()

            # --- ВИЗУАЛИЗАЦИЯ ---

            # 1. Точка указательного пальца
            if frame_data.index_finger_x != -1 and frame_data.index_finger_y != -1:
                cv2.circle(display_frame, (frame_data.index_finger_x, frame_data.index_finger_y), 10, (0, 255, 0), -1)
                cv2.putText(display_frame, "📌", (frame_data.index_finger_x - 15, frame_data.index_finger_y - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 2. Текст с информацией
            info_lines = [
                f"🎯 Жест: {frame_data.gesture}",
                f"⏱ Latency: {frame_data.latency_ms:.1f} ms",
                f"📈 FPS: {frame_data.fps:.1f}",
                f"✋ Ладонь: {frame_data.is_palm_open}",
                f"🤏 Pinch: {frame_data.is_pinch_active}",
                f"📍 Палец: ({frame_data.index_finger_x}, {frame_data.index_finger_y})",
            ]

            if frame_data.num_hands_detected >= 2:
                info_lines.append(f"📏 Масштаб: x{frame_data.scale_factor:.2f}")
                info_lines.append(f"📏 Расстояние: {frame_data.hands_distance_px:.1f} px")

            # Рисуем текст на кадре
            y_offset = 30
            for line in info_lines:
                cv2.putText(display_frame, line, (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
                y_offset += 25

            # Показываем кадр
            cv2.imshow('Smart Canvas - Gesture Feed', display_frame)

            # --- ВЫВОД В КОНСОЛЬ ---
            print(f"\n--- КАДР {frame_count} ---")
            print(f"⏱ Latency: {frame_data.latency_ms:.2f} ms")
            print(f"📈 FPS: {frame_data.fps:.1f}")
            print(f"🎯 Жест: {frame_data.gesture}")
            print(f"✋ Ладонь открыта: {frame_data.is_palm_open}")
            print(f"🤏 Pinch активен: {frame_data.is_pinch_active}")
            print(f"📍 Указательный палец: ({frame_data.index_finger_x}, {frame_data.index_finger_y})")

            if frame_data.num_hands_detected >= 2:
                print(f"📏 Масштаб: x{frame_data.scale_factor:.2f}")
                print(f"📏 Расстояние между руками: {frame_data.hands_distance_px:.1f} px")

            # --- УПРАВЛЕНИЕ ---
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            # Пауза для удобства чтения (можно закомментировать)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n🛑 Тест остановлен пользователем.")

    finally:
        camera.release()
        cv2.destroyAllWindows()
        elapsed = time.perf_counter() - start_time
        print(f"\n📊 Итоги:")
        print(f"⏱ Общее время: {elapsed:.1f} сек")
        print(f"🖼 Обработано кадров: {frame_count}")
        if elapsed > 0:
            print(f"📈 Средний FPS: {frame_count / elapsed:.1f}")

if __name__ == "__main__":
    main()