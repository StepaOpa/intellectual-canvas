# intellectual-canvas

## Гайд по билду проекта


### Шаги
#### 1. Создайте виртуальное окружение:
```
python -m venv .venv

source .venv/bin/activate
```
#### 2. Установите зависимости:
```
pip install -r requirements.txt
```
#### 3. Выполните билд:
```
pyinstaller --onefile --collect-all mediapipe main.py
```