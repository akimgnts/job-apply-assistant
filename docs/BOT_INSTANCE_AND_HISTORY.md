# 🤖 Bot Instance Management & Conversation History

## Problem Solved

**Problem:** When restarting the bot, two instances would poll Telegram API simultaneously → 409 Conflict errors blocking messages.

**Root Cause:**
- Old bot instance didn't die when new one started
- Only one instance per bot token allowed on Telegram API
- Both competed to poll → conflict

**Solution:** 
- Singleton lock system - only 1 instance can run
- New instance kills the old one on startup
- Complete conversation history for audit trail

---

## Architecture

### 1. Bot Instance Manager

**File:** `app/services/bot_instance_manager.py`

#### How It Works

```
New Bot Starts
    ↓
acquire_lock()
    ↓
Is PID file present?
    ├─ YES → Check if old process still running
    │         ├─ YES → Kill old process (SIGTERM, then SIGKILL)
    │         └─ NO → Continue
    ├─ NO → Continue
    ↓
Write new PID file
    ↓
record_instance("started")
    ↓
Run polling
```

#### API

```python
# Acquire singleton lock at startup
BotInstanceManager.acquire_lock()

# Record lifecycle events
BotInstanceManager.record_instance(db, "started", "Bot instance acquired lock")
BotInstanceManager.record_instance(db, "stopped", "Graceful shutdown")
BotInstanceManager.record_instance(db, "error", error_message)

# Cleanup on shutdown
BotInstanceManager.cleanup_on_shutdown(db)
```

#### Database Schema

```sql
CREATE TABLE bot_instances (
    id INTEGER PRIMARY KEY,
    pid INTEGER NOT NULL,           -- Process ID
    status VARCHAR(50) NOT NULL,    -- 'started', 'stopped', 'error'
    message TEXT,                   -- Optional details
    timestamp DATETIME NOT NULL     -- When event occurred
);
```

---

### 2. Conversation History Service

**File:** `app/services/conversation_history_service.py`

#### Purpose

Record **every** interaction:
- User messages
- Bot replies
- Button callbacks  
- Errors

Enables:
- Complete audit trail
- Debugging problematic conversations
- Replay/test scenarios
- User support (reconstruct lost context)

#### API

```python
from app.services.conversation_history_service import ConversationHistoryService

# Record user message
ConversationHistoryService.record_user_message(
    db, 
    user_id="1045502137",
    text="/start",
    command="start"
)

# Record bot reply
ConversationHistoryService.record_bot_reply(
    db,
    user_id="1045502137", 
    text="Welcome!",
    buttons=["Analyze Offer", "View Profile"]
)

# Record button callback
ConversationHistoryService.record_callback(
    db,
    user_id="1045502137",
    callback_data="intelligence_menu",
    response="Opening menu..."
)

# Record error
ConversationHistoryService.record_error(
    db,
    user_id="1045502137",
    error_message="KeyError: total_active_offers",
    error_type="KeyError",
    context={"api": "elevia_intelligence"}
)

# Query history
history = ConversationHistoryService.get_user_history(
    db, 
    user_id="1045502137",
    limit=50,
    message_type="error"  # optional filter
)

# Get formatted flow
flow = ConversationHistoryService.get_conversation_flow(
    db,
    user_id="1045502137",
    limit=20
)
print(flow)
# 👤 [21:25:01] user_message
#    /start
# 🤖 [21:25:02] bot_reply
#    Welcome!
# 🔘 [21:25:03] callback
#    Button pressed: intelligence_menu
# 🤖 [21:25:04] bot_reply
#    Opening Intelligence Agent...
```

#### Database Schema

```sql
CREATE TABLE conversation_history (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,  -- Indexed for fast lookups
    message_type VARCHAR(50),        -- 'user_message', 'bot_reply', 'callback', 'error'
    content TEXT NOT NULL,           -- The actual message/error
    metadata JSON,                   -- Extra data (command, button_pressed, error_type, etc)
    timestamp DATETIME NOT NULL      -- Indexed for range queries
);

-- Indexes
CREATE INDEX ix_conversation_history_user_id ON conversation_history(user_id);
CREATE INDEX ix_conversation_history_timestamp ON conversation_history(timestamp);
```

---

## Implementation in Bot

### telegram_bot.py Changes

```python
from app.services.bot_instance_manager import BotInstanceManager
from app.database.db import SessionLocal

def main():
    """Start the bot with singleton instance management."""
    db = SessionLocal()
    try:
        # Step 1: Acquire singleton lock (kills old instance)
        BotInstanceManager.acquire_lock()
        BotInstanceManager.record_instance(db, "started", "Bot instance acquired lock")

        logger.info("Starting Job Apply Assistant bot...")
        app = setup_bot()

        # ... signal handlers ...

        try:
            app.run_polling(allowed_updates=[])  # Only 1 instance polling
        except Exception as e:
            BotInstanceManager.record_instance(db, "error", str(e))
        finally:
            # Step 2: Cleanup on shutdown
            BotInstanceManager.cleanup_on_shutdown(db)  # Releases lock + records stop
    finally:
        db.close()
```

---

## Integration Points

### Handler Integration Example

To add conversation history to existing handlers:

```python
# In any Telegram handler
from app.services.conversation_history_service import ConversationHistoryService

async def handle_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    db = SessionLocal()
    
    try:
        # Record user input
        ConversationHistoryService.record_user_message(
            db,
            user_id=user_id,
            text=update.message.text,
            command=None
        )
        
        # Do the work...
        analysis = await AnalysisAgent.analyze(db, offer_text)
        
        # Record bot response
        ConversationHistoryService.record_bot_reply(
            db,
            user_id=user_id,
            text=formatted_response,
            buttons=["Generate", "Save", "Analyze More"]
        )
        
        await update.message.reply_text(formatted_response, reply_markup=menu)
        
    except Exception as e:
        # Record error
        ConversationHistoryService.record_error(
            db,
            user_id=user_id,
            error_message=str(e),
            error_type=type(e).__name__,
            context={"handler": "handle_offer"}
        )
        await update.message.reply_text(f"Error: {e}")
    finally:
        db.close()
```

---

## Deployment Workflow

### 1. Rolling Update (New)

```bash
# Current: Old bot running (PID 1234)
docker-compose up -d --no-deps --build app

# What happens:
# 1. Docker starts new container (PID 5678)
# 2. New bot calls acquire_lock()
# 3. Lock manager sees old PID 1234 still running
# 4. Lock manager kills old process (SIGTERM)
# 5. After 2 seconds, if still running: SIGKILL
# 6. New bot writes PID 5678 to lock file
# 7. New bot is now polling (no conflict!)
```

### 2. Manual Restart

```bash
# Just run the bot
python -m app.bot.telegram_bot

# Or with docker
docker run job-apply-assistant
```

No manual intervention needed - singleton lock handles everything.

---

## Debugging with History

### View Conversation for User

```python
from app.database.db import SessionLocal
from app.services.conversation_history_service import ConversationHistoryService

db = SessionLocal()
user_id = "1045502137"

# Get recent 50 messages
history = ConversationHistoryService.get_user_history(db, user_id, limit=50)

for msg in history:
    print(f"[{msg.timestamp}] {msg.message_type}: {msg.content}")

# Get formatted flow
flow = ConversationHistoryService.get_conversation_flow(db, user_id, limit=20)
print(flow)
```

### Find Errors in Last 24h

```python
from datetime import datetime, timedelta

cutoff = datetime.utcnow() - timedelta(hours=24)

errors = db.query(ConversationHistory).filter(
    ConversationHistory.message_type == "error",
    ConversationHistory.timestamp >= cutoff
).order_by(ConversationHistory.timestamp.desc()).all()

for error in errors:
    print(f"User {error.user_id} at {error.timestamp}")
    print(f"  Error: {error.content}")
    print(f"  Type: {error.metadata.get('error_type')}")
```

---

## Benefits

| Feature | Benefit |
|---------|---------|
| **Singleton Lock** | Only 1 instance polling → no 409 conflicts |
| **Auto-kill old instance** | Zero downtime deployments |
| **Conversation History** | Complete audit trail for debugging |
| **Error Recording** | Track issues across all users |
| **Metadata support** | Rich context in history (buttons, commands, etc) |
| **Database indexed** | Fast queries by user_id or time range |

---

## Files Modified

- `app/services/bot_instance_manager.py` — Singleton lock management
- `app/services/conversation_history_service.py` — Conversation recording
- `app/database/models.py` — New tables: BotInstance, ConversationHistory
- `app/bot/telegram_bot.py` — Integrated singleton lock at startup
- `migrations/versions/007_add_bot_tracking.py` — Database migration

---

## Next Steps

1. **Run migration:** `alembic upgrade head`
2. **Deploy new code:** `docker-compose up -d --build`
3. **Check bot logs:** Should see "Bot instance lock acquired"
4. **Test conversation history:** Query ConversationHistory table

---

## Troubleshooting

### Bot won't start

Check if `/tmp/job_apply_bot.pid` contains a stale PID:
```bash
cat /tmp/job_apply_bot.pid
ps aux | grep <pid>  # If process doesn't exist, delete PID file
rm /tmp/job_apply_bot.pid
```

### No conversation history recorded

Make sure handlers call ConversationHistoryService methods. Example integration above.

### Still getting 409 conflicts

Wait for old instance to fully shutdown (10s grace period). If still failing:
```bash
pkill -f "python.*telegram_bot"  # Force kill all
sleep 2
python -m app.bot.telegram_bot   # Start fresh
```

---

**Result:** A single, stable bot instance with complete conversation audit trail. ✅
