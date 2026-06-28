# 🚀 Bot Deployment Issue - Fixed

## Problem

When deploying a new version of the bot (rolling update), the logs showed:
```
Conflict: terminated by other getUpdates request
```

This error occurred repeatedly every 5-6 seconds, preventing the new bot instance from receiving Telegram messages.

### Root Cause

When Docker deployed a new bot container, the old container was still running with `app.run_polling()` actively polling Telegram's API. The Telegram API only allows one instance per bot token to poll at a time. Both instances tried to poll simultaneously → conflict.

The old container wasn't gracefully shutting down before the new one started because:
1. Signal handlers weren't defined in telegram_bot.py
2. Docker's default stop timeout might have been too short
3. No coordination between shutdown and polling loop

## Solution

### 1. Added Graceful Shutdown Handlers

**File: `app/bot/telegram_bot.py`**

```python
import signal

def main():
    """Start the bot with graceful shutdown support."""
    logger.info("Starting Job Apply Assistant bot...")
    app = setup_bot()

    def stop_bot(signum, frame):
        """Handle graceful shutdown on SIGTERM."""
        logger.info(f"Received signal {signum}, stopping bot gracefully...")
        app.stop()

    signal.signal(signal.SIGTERM, stop_bot)
    signal.signal(signal.SIGINT, stop_bot)

    try:
        app.run_polling(allowed_updates=[])
    except Exception as e:
        logger.error(f"Bot encountered error: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped")
```

**What this does:**
- Registers handlers for SIGTERM (Docker graceful stop) and SIGINT (Ctrl+C)
- When Docker sends SIGTERM, `stop_bot()` is called
- Calls `app.stop()` to cleanly close the polling connection
- Logs the shutdown for debugging

### 2. Updated Docker Compose

**File: `docker-compose.yml`**

```yaml
app:
  # ... other config ...
  stop_signal: SIGTERM
  stop_grace_period: 30s
```

**What this does:**
- `stop_signal: SIGTERM` — Docker explicitly sends SIGTERM on shutdown
- `stop_grace_period: 30s` — Docker waits 30 seconds for graceful shutdown before force-killing

This ensures the old container has time to cleanly close its polling connection before the new one starts.

## Deployment Flow (After Fix)

1. **Deploy new version** → Docker starts new container
2. **Docker detects new instance** → Sends SIGTERM to old container
3. **Old bot's signal handler** → Calls `app.stop()` to close polling
4. **Polling connection closes** → Telegram API releases the slot
5. **New bot starts polling** → No conflict ✅
6. **After 30s** → Docker force-kills old container if needed (cleanup)

## Testing the Fix

To verify graceful shutdown works:

```bash
# In one terminal, start the bot
python -m app.bot.telegram_bot

# In another terminal, send SIGTERM
kill -TERM <pid>

# Should see in logs:
# "Received signal 15, stopping bot gracefully..."
# "Bot stopped"
```

## Deployment Checklist

- [x] Graceful shutdown handlers added
- [x] Docker compose stop config updated
- [x] Changes committed and pushed to master
- [x] Ready for rolling deployment

## Related Files

- `app/bot/telegram_bot.py` — Signal handler implementation
- `docker-compose.yml` — Deployment configuration
- Commit: `801ebb2` — "fix: add graceful shutdown for bot"

---

**Impact:** This fix enables clean rolling deployments without the 409 Conflict errors. The bot can now update without losing message connectivity.
