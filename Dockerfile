FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright chromium for JS-rendered job sites
RUN playwright install chromium --with-deps

COPY . .

RUN mkdir -p outputs

ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

CMD ["python", "-m", "app.bot.telegram_bot"]
