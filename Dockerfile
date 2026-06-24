FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    # Playwright/Chromium dependencies (Debian trixie package names)
    fonts-unifont \
    libnss3 \
    libnspr4 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2t64 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    libatspi2.0-0t64 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libdrm2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright chromium (best-effort: falls back to trafilatura if binary unavailable)
RUN playwright install chromium || echo "Playwright chromium install skipped (network restricted)"

COPY . .

RUN mkdir -p outputs

ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

CMD ["python", "-m", "app.bot.telegram_bot"]
