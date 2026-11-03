FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE=/data/library.db
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# run as a non-root user; /data holds the SQLite file (mounted as a volume)
RUN useradd -m appuser && mkdir /data && chown appuser /data
USER appuser

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:5000/health')"

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "app.main:app"]
