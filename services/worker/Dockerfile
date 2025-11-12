FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# langflow_queue будет смонтирован через volume в docker-compose.yml
ENV PYTHONPATH=/app

CMD ["python", "worker_runner.py"]

