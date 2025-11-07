import time

class MetricsCollector:
    def __init__(self):
        self.fps_buffer = []
        self.start_time = time.perf_counter()

    def calculate_fps(self):
        current_time = time.perf_counter()
        elapsed = current_time - self.start_time
        fps = len(self.fps_buffer) / elapsed if elapsed > 0 else 0
        self.fps_buffer.append(current_time)
        if len(self.fps_buffer) > 100:
            self.fps_buffer.pop(0)
        return fps

    def reset(self):
        self.fps_buffer.clear()
        self.start_time = time.perf_counter()