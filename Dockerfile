FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY app ./app
COPY migrations ./migrations
COPY wsgi.py sync_contract.py ./
RUN useradd --create-home album && mkdir -p /app/instance && chown -R album:album /app
USER album
EXPOSE 5000
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "--call", "app:create_app"]
