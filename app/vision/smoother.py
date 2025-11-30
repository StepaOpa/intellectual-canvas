import numpy as np
import time

class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.05, d_cutoff=1.0):
        """
        min_cutoff: Минимальная частота среза. Меньше = плавнее, но больше задержка.
                    1.0 подходит для медленного рисования.
        beta: Коэффициент скорости. Больше = быстрее реагирует на резкие движения.
              Увеличили с 0.0 до 0.05, чтобы палец не "плавал" при быстрых штрихах.
        """
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None

    def smooth_point(self, x: float, y: float):
        """Сглаживает одну точку (x, y)."""
        t = time.perf_counter()
        
        # Если это первый кадр
        if self.x_prev is None:
            self.x_prev = np.array([x, y])
            self.dx_prev = np.zeros(2)
            self.t_prev = t
            return x, y

        dt = t - self.t_prev
        if dt <= 0:
            return self.x_prev[0], self.x_prev[1]

        current_val = np.array([x, y])
        dx = (current_val - self.x_prev) / dt

        # Вычисляем коэффициент alpha динамически
        edx = np.linalg.norm(self.dx_prev) # Скорость изменения
        cutoff = self.min_cutoff + self.beta * np.abs(edx)
        alpha = self._alpha(dt, cutoff)

        # Основная формула фильтрации
        filtered_val = alpha * current_val + (1.0 - alpha) * self.x_prev
        
        # Сглаживаем и производную (скорость)
        alpha_d = self._alpha(dt, self.d_cutoff)
        filtered_dx = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev

        # Сохраняем состояние
        self.x_prev = filtered_val
        self.dx_prev = filtered_dx
        self.t_prev = t

        return filtered_val[0], filtered_val[1]

    def reset(self):
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None

    def _alpha(self, dt, cutoff):
        tau = 1.0 / (2 * np.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)