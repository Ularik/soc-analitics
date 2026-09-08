FROM python:3.12.2-slim

WORKDIR /app

# Сначала ставим зависимости (используем кэш, пока requirements.txt не изменится)
COPY . .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Запуск через uvicorn
#CMD alembic upgrade head; python src/main.py
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]