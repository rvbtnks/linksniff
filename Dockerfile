# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

WORKDIR /app

RUN pip install --no-cache-dir \
      flask \
      apscheduler \
      yt-dlp \
      playwright==1.51.0 \
      requests \
      gunicorn

COPY app.py .
COPY templates/ ./templates/
COPY static/    ./static/

EXPOSE 9559

CMD ["gunicorn", "--bind", "0.0.0.0:9559", "app:app"]
