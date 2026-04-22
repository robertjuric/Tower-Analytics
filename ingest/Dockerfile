FROM python:3.11

WORKDIR /app

COPY ingest.py .

RUN pip install psycopg2-binary watchdog

CMD ["python", "ingest.py"]