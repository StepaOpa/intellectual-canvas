import time

class MetricsCollector:
    def __init__(self):
        self.frame_times = []

    def update(self):
        """Вызывается каждый кадр. Возвращает текущий FPS."""
        current_time = time.perf_counter()
        self.frame_times.append(current_time)

        # Оставляем только последние 30 кадров (примерно ~1 сек при 30 FPS)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)

        if len(self.frame_times) < 2:
            return 0.0

        # FPS = (число кадров - 1) / (время между первым и последним)
        elapsed = self.frame_times[-1] - self.frame_times[0]
        if elapsed <= 0:
            return 0.0
        return (len(self.frame_times) - 1) / elapsed