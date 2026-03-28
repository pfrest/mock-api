FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 5000

ENV MOCKS_DIR=/mocks

CMD ["python", "-m", "hypercorn", "--bind", "0.0.0.0:5000", "app.app:create_app()"]
