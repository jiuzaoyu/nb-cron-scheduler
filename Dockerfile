FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/
COPY jobs/ jobs/

EXPOSE 8088

CMD ["python", "-m", "uvicorn", "src.app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8088"]
