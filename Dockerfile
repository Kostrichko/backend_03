FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости для backend
COPY backend/requirements.txt ./backend_requirements.txt
RUN pip install --no-cache-dir -r backend_requirements.txt

# Устанавливаем зависимости для bot
COPY bot/requirements.txt ./bot_requirements.txt
RUN pip install --no-cache-dir -r bot_requirements.txt

# Копируем код
COPY backend/ ./backend/
COPY bot/ ./bot/

EXPOSE 8000