import sys
import os

# Добавляем корень проекта в путь поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.core.core import AppCore

if __name__ == "__main__":
    core = AppCore(sys.argv)
    sys.exit(core.run())