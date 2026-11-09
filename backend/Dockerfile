FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --system --home-dir /app --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
# 2 workers x maximum (5 pool + 2 overflow) = up to 14 PG connections
# across the API, excluding background workers. Tune from measured capacity.
CMD ["gunicorn", "--workers", "2", "--threads", "2", "--worker-class", "gthread", \
     "--timeout", "30", "--graceful-timeout", "15", "--keep-alive", "5", \
     "--max-requests", "1000", "--max-requests-jitter", "150", \
     "--access-logfile", "/dev/null", "--error-logfile", "-", \
     "--bind", "0.0.0.0:8000", "wsgi:app"]
