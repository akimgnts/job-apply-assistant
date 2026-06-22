# Audit Ciblé - Bot Telegram Non Responsive

## Problème Rapporté

**Symptôme**: Bot Telegram lance sans erreur visible ("Application started"), mais ne répond à AUCUN message:
- `/start` → Aucune réponse
- `/help` → Aucune réponse  
- Message texte "cher chauffeur" → Aucune réponse
- `/debug` → Aucune réponse

**Logs du Bot**: 
```
2026-06-22 22:52:28 - Application started
HTTP/1.1 200 OK (getMe, deleteWebhook)
```
Puis silence complet. Aucun log quand messages reçus.

---

## État Actuel du Codebase

### Commits Récents
```
64bbd3a - docs: Database setup & connection diagnostics for Coolify integration
0f6c020 - refactor: Telegram UI/UX - Clean, structured message formatting ← SUSPECT
3eff5ed - fix: Critical + High priority stabilization (P1+P2)
2555a32 - feat: Phase 5.4 - Profile upload workflow for Elevia integration
...
```

Le commit `0f6c020` (UI/UX refactor) a modifié:
- `app/bot/handlers.py`
- `app/bot/message_formatter.py`

### Structure Bot

**File**: `app/bot/telegram_bot.py`
- Crée `Application`
- Enregistre handlers pour `/start`, `/help`, `/last`
- Enregistre `MessageHandler` pour texte: `filters.TEXT & ~filters.COMMAND`
- Lance `app.run_polling(allowed_updates=[])`

**File**: `app/bot/handlers.py`
- `start_command()` → appelle `format_home_message()` + envoie réponse
- `help_command()` → retourne texte HTML
- `last_command()` → cherche dernière app en DB
- `handle_offer()` → process offre (InputAgent → AnalysisAgent → save DB)
- `handle_command()` → handle `GO`, `CV`, `LETTRE`, `MAIL`

**File**: `app/bot/message_formatter.py`
- Formats all Telegram messages
- Recent refactor added HTML markup + emojis
- All functions return `(text, parse_mode)` tuple

### Database Setup
- PostgreSQL 16.14 lancé via Brew sur localhost:5432
- DB: `job_apply_db`, user: `jobapply`, password: `password`
- Migrations appliquées: `alembic upgrade head` ✓
- Profile blocks seeded: `python -m app.database.seed_profile` ✓
- Connection verified: `test_db_connection.py` ✓

### Environment
- Python 3.14
- Telegram Bot Token: Valid (tested `getMe` → 200 OK)
- OpenAI API Key: Valid (in .env)
- DATABASE_URL: `postgresql://jobapply:password@localhost:5432/job_apply_db`

---

## Possibilités Diagnostiquées

### 1. Handler Non Enregistré / Crash Silencieux
- Bot lance sans erreur
- Handlers déclarés mais peut-être pas exécutés
- Exceptions non catchées (no error_handler registered)

**À vérifier**:
```python
# telegram_bot.py logs handler registration
# Add debug logging before/after each handler
```

### 2. MessageHandler Filtre Trop Restrictif
```python
MessageHandler(filters.Regex("^(GO|CV|LETTRE|MAIL)$"), handle_command)
MessageHandler(filters.TEXT & ~filters.COMMAND, handle_offer)
```

Second handler = texte NON-commande. `/help` est commande = pas catchée par ce handler. Mais `/help` a propre `CommandHandler` enregistré.

**À vérifier**: CommandHandler vs MessageHandler order/conflicts

### 3. Polling Update Filter Issue
```python
app.run_polling(allowed_updates=[])
```

`allowed_updates=[]` = liste vide = ??? Peut-être bloque tous les updates?

**Standard**: `allowed_updates=["message", "callback_query"]` ou None (par défaut)

### 4. Database Connection Deadlock
- `handle_offer()` crée `SessionLocal()` pas fermée dans tous les chemins
- DB timeout si query longue (OpenAI call)
- Silent failure si DB unavailable

### 5. OpenAI Timeout / Hang
- `AnalysisAgent.analyze()` appelle OpenAI API (~2-5s)
- Si OpenAI timeout, handler hang → pas de réponse utilisateur
- Logs show "Application started" mais handlers en attente

### 6. Async/Await Mismatch
- Handlers sont `async def`
- Mais certaines dépendances peut-être pas async
- Deadlock possible

---

## Commandes d'Audit Recommandées

### Phase 1: Verify Bot Reachability
```bash
# Check if Telegram is sending updates
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from app.bot.telegram_bot import setup_bot
app = setup_bot()
print(f'Handlers registered: {len(app.handlers)}')
for handler_list in app.handlers:
    print(f'  {handler_list}')
"
```

### Phase 2: Test Handler Directly
```python
# Test start_command without Telegram
from unittest.mock import AsyncMock, MagicMock
from app.bot.handlers import start_command

update = MagicMock()
context = AsyncMock()
update.effective_user.id = "12345"
update.message.reply_text = AsyncMock()

await start_command(update, context)
print(f"Reply called: {update.message.reply_text.called}")
print(f"Reply args: {update.message.reply_text.call_args}")
```

### Phase 3: Test Database Connection in Handler
```python
from app.database.db import SessionLocal
from app.database.models import ProfileBlock

db = SessionLocal()
blocks = db.query(ProfileBlock).count()
print(f"Profile blocks in DB: {blocks}")
db.close()
```

### Phase 4: Add Debug Logging
**Insert into handlers.py**:
```python
logger.info(f"[HANDLER] start_command called by user {update.effective_user.id}")
logger.info(f"[HANDLER] Sending message...")
logger.info(f"[HANDLER] Message sent, returning")
```

**Insert into telegram_bot.py**:
```python
def setup_bot():
    ...
    # Add error handler
    async def error_handler(update, context):
        logger.error(f"Error: {context.error}")
    app.add_error_handler(error_handler)
    
    # Log all updates received
    from telegram.ext import BaseUpdate
    app.add_handler(
        MessageHandler(filters.ALL, 
                      lambda u, c: logger.info(f"[UPDATE] {u.message.text[:50]}"))
    )
    ...
```

### Phase 5: Test Polling Loop
```bash
# Run bot with verbose logging
LOG_LEVEL=DEBUG python -m app.bot.telegram_bot
# Then send /start
# Monitor logs for: update received, handler called, message sent
```

---

## Hipótesis Prioritarias

**P0 CRITICAL**:
1. `allowed_updates=[]` blocking all updates in polling
2. OpenAI API call hanging forever (no timeout)
3. Database connection exhausted (SessionLocal not closed)

**P1 HIGH**:
4. Handler crash with no error logging
5. MessageHandler filter too restrictive
6. Async/await deadlock in dependency chain

**P2 MEDIUM**:
7. Import error (handler function not found)
8. Configuration issue (token invalid, etc)

---

## Fichiers à Inspecter

### Critical
- `app/bot/telegram_bot.py` → Check `allowed_updates`, error_handler, handler registration
- `app/bot/handlers.py` → Check exception handling, database closing, async/await
- `app/services/openai_service.py` → Check timeout on API calls

### Important
- `app/database/db.py` → Check SessionLocal behavior
- `app/agents/input_agent.py` → Check if `InputAgent.process()` is async
- `app/agents/analysis_agent.py` → Check if timeout set on OpenAI call

### Reference
- `.env` → Verify TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, DATABASE_URL
- `requirements.txt` → Check python-telegram-bot version compatibility

---

## Prochaines Étapes

1. **Run Phase 1 audit**: Verify bot structure
2. **Run Phase 2 audit**: Test handlers directly  
3. **Run Phase 4 audit**: Add debug logging everywhere
4. **Run Phase 5 audit**: Start bot with debug logs and send /start
5. **Analyze logs**: Find exactly where execution stops

**Expected outcome**: 
- Logs showing exactly which handler is called
- Or logs showing which handler is NOT called
- Or logs showing where handler crashes
- Or discovery that polling isn't receiving updates

---

## Success Criteria

Bot responds to `/start` with formatted message within 2 seconds.
