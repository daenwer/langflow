FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# langflow_queue will be mounted via volume in docker-compose.yml
ENV PYTHONPATH=/app

CMD ["python", "worker_runner.py"]

