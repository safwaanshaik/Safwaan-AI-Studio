web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout 600
worker: celery -A backend.app.workers.gen_worker worker --concurrency=1 --pool=solo