import numpy as np
import time

class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None

    def smooth_landmarks(self, landmarks):
        if self.x_prev is None:
            self.x_prev = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
            self.dx_prev = np.zeros_like(self.x_prev)
            self.t_prev = 0.0
            return landmarks

        t = time.perf_counter()
        dt = t - self.t_prev
        if dt <= 0:
            return landmarks

        x = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
        dx = (x - self.x_prev) / dt

        alpha = self._alpha(dt, self.min_cutoff)
        filtered_x = alpha * x + (1 - alpha) * self.x_prev

        alpha_d = self._alpha(dt, self.d_cutoff)
        filtered_dx = alpha_d * dx + (1 - alpha_d) * self.dx_prev

        # Update
        self.x_prev = filtered_x
        self.dx_prev = filtered_dx
        self.t_prev = t

        # Заменяем координаты в оригинальных landmark'ах
        for i, lm in enumerate(landmarks):
            lm.x = filtered_x[i, 0]
            lm.y = filtered_x[i, 1]
            lm.z = filtered_x[i, 2]

        return landmarks

    def _alpha(self, dt, cutoff):
        tau = 1.0 / (2 * np.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)