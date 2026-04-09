FROM python:3.13.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

CMD ["python", "-m", "tests.test"]
