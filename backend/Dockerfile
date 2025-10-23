FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 git
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["gunicorn", "app.main:app", "--workers", "1", "--timeout", "600", "--bind", "0.0.0.0:8000"]
