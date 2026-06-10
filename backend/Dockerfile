FROM python:3.14.2-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY db ./db

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "echo \"Starting AI Trust Analyzer on port ${PORT:-8000}\" && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
