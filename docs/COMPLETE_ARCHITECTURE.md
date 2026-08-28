# 🏗️ Job Apply Assistant - Architecture Complète

**Version:** 2026-06-29  
**Stack:** Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL + Telegram Bot

---

## 📊 Vue d'Ensemble

```
Utilisateur Telegram
    ↓
Telegram Bot (polling/webhooks)
    ↓
Handlers (orchestration)
    ↓
Agents (business logic)
    ↓
Services (APIs, DB, files)
    ↓
Database + External APIs
```

---

## 🔄 Flux Principal: Analyse d'une Offre d'Emploi

### Étape 1: Utilisateur Envoie une Offre

```
👤 Utilisateur Telegram
    ↓
    Colle une offre URL ou texte
    ↓
/start → Main Menu
    ↓
Envoie: "Senior Data Engineer..."
```

### Étape 2: Bot Reçoit le Message

**Fichier:** `app/bot/handlers.py`

```python
# handlers.py: handle_offer()
async def handle_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    offer_text = update.message.text
    db = SessionLocal()
    
    # 1. Crée un application record
    app = create_application(db, user_id, offer_text)
    # → DB: applications table (id, user_id, raw_offer, ...)
```

### Étape 3: Analyse de l'Offre

```python
    # 2. Appelle l'agent d'analyse
    analysis = await AnalysisAgent.analyze(db, offer_text)
    # ↓
    # Envoie à OpenAI: "Analyse cette offre"
    # ← OpenAI retourne JSON structuré:
    # {
    #   "job_title": "Senior Data Engineer",
    #   "company": "Stripe",
    #   "required_skills": ["Python", "SQL", "AWS"],
    #   "missing_points": ["Kubernetes"],
    #   "match_score": 8.5,
    #   ...
    # }
```

**Agents impliqués:**

| Agent | Rôle | Input | Output |
|-------|------|-------|--------|
| `AnalysisAgent` | Extrait infos offre | offer_text | JSON analysis |
| `MatchingAgent` | Valide skills vs profile | analysis + profile_blocks | enriched_analysis |
| `PositioningAgent` | Choisit angle de candidature | analysis | positioning (ex: "BI Expert") |
| `GenerationAgent` | Génère CV/lettre/mail | analysis + positioning | HTML/text |
| `QualityAgent` | Vérifie pas d'invention | generated_docs | "SAFE" / "REVIEW" / "REJECT" |

### Étape 4: Enrichissement

```python
    # 3. Enrichit avec profil utilisateur
    analysis = MatchingAgent.enrich_analysis(analysis, db)
    # Valide que les skills requises existent dans profile_blocks
    
    # 4. Choisit le meilleur angle
    positioning = await PositioningAgent.choose_angle(analysis)
    # "Vous appliquez comme: Data Analyst BI"
    
    # 5. Sauvegarde l'analyse
    save_analysis(db, app.id, analysis)
    update_application_with_analysis(db, app.id, analysis)
```

### Étape 5: Affichage au Bot

```python
    # 6. Formate la réponse
    text = format_analysis_message(
        job_title=analysis["job_title"],
        company=analysis["company"],
        positioning=positioning,
        match_score=app.match_score,
        strengths=analysis["strengths"],
        weaknesses=analysis["missing_points"]
    )
    
    # 7. Envoie avec boutons
    await update.message.reply_text(
        text,
        reply_markup=offer_extracted_menu(app.id)  # Boutons: Générer, Sauvegarder, etc
    )
```

### Étape 6: Utilisateur Clique sur Bouton

```
🔘 Utilisateur clique "📄 Générer Candidature"
    ↓
CallbackQueryHandler reçoit le callback_data="gen_all:123"
    ↓
gen_all_callback() dans handlers.py
```

### Étape 7: Génération des Documents

```python
async def gen_all_callback(update, context):
    app_id = extract_app_id(callback_data)
    analysis = get_analysis(db, app_id)
    
    # 1. Génère CV
    cv_html = await GenerationAgent.generate_cv(
        db, 
        app_id,
        analysis,
        positioning="Data Analyst BI"
    )
    # → Template Jinja2 + OpenAI content
    
    # 2. Génère Lettre de Motivation
    letter_html = await GenerationAgent.generate_letter(...)
    
    # 3. Génère Email
    mail_text = await GenerationAgent.generate_mail(...)
    
    # 4. Enregistre les fichiers
    save_document(db, app_id, "cv", cv_html)
    save_document(db, app_id, "letter", letter_html)
    save_document(db, app_id, "mail", mail_text)
    
    # 5. Affiche au bot avec boutons de téléchargement
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "✅ Documents générés!\n\n📥 Télécharger:",
        reply_markup=document_menu(app_id)
    )
```

---

## 🗄️ Schéma de Base de Données

### Tables Principales

```sql
-- Profil utilisateur (blocs de contenu)
profile_blocks
├─ id (PK)
├─ category (skill, experience, project, education, ...)
├─ title ("Python", "5 ans Django", "Project X", ...)
├─ content (description)
├─ tags (["backend", "api"])
├─ priority (1-10)
├─ truth_level (verified, project, in_progress, learning)
└─ created_at, updated_at

-- Candidatures (une par offre analysée)
applications
├─ id (PK)
├─ telegram_user_id
├─ company
├─ job_title
├─ raw_offer (le texte copié)
├─ source_url (si URL)
├─ recommended_angle
├─ match_score (0-100)
├─ status (analyzed, generated, saved, archived)
└─ created_at, updated_at

-- Analyse structurée (JSON)
job_analysis
├─ id (PK)
├─ application_id (FK)
├─ analysis_json (JSONB)
│  ├─ job_title
│  ├─ company
│  ├─ required_skills
│  ├─ soft_skills
│  ├─ missing_points
│  ├─ ats_keywords
│  └─ ...
└─ created_at

-- Documents générés (CV, lettre, mail)
generated_documents
├─ id (PK)
├─ application_id (FK)
├─ document_type (cv, letter, mail)
├─ filename
├─ content (HTML ou texte)
├─ file_path (/outputs/...)
└─ created_at

-- État utilisateur (session)
user_sessions
├─ id (PK)
├─ telegram_user_id
├─ last_application_id (FK)
├─ state (idle, waiting_for_command, ...)
├─ session_data (JSONB - données temporaires)
└─ created_at, updated_at

-- ⭐ NOUVEAU: Instance du bot
bot_instances (NEW)
├─ id (PK)
├─ pid (process ID)
├─ status (started, stopped, error)
├─ message (details)
└─ timestamp

-- ⭐ NOUVEAU: Historique des conversations
conversation_history (NEW)
├─ id (PK)
├─ user_id
├─ message_type (user_message, bot_reply, callback, error)
├─ content
├─ metadata (JSON)
└─ timestamp (indexed)
```

---

## 🤖 Agents (Business Logic)

### 1. AnalysisAgent

**Rôle:** Analyser une offre d'emploi  
**Input:** Texte brut de l'offre  
**Process:**
1. Envoie à OpenAI avec prompt d'analyse
2. Parse la réponse JSON
3. Extrait: skills, missions, soft skills, gaps, etc

**Output:** `{ job_title, company, required_skills, missing_points, ats_keywords, ... }`

### 2. MatchingAgent

**Rôle:** Enrichir l'analyse avec profil utilisateur  
**Input:** analysis + profile_blocks de la DB  
**Process:**
1. Récupère tous les profile_blocks
2. Valide que les skills required existent
3. Marque les skills présentes vs absentes
4. Calcule match_score

**Output:** analysis enrichie avec profile match

### 3. PositioningAgent

**Rôle:** Choisir l'angle de candidature  
**Input:** analysis enrichie  
**Process:**
1. 7 angles fixes (Data Analyst, Backend Engineer, Full Stack, etc)
2. Envoie à OpenAI: "Quel angle choisir pour cette offre?"
3. OpenAI retourne meilleur angle

**Output:** "Data Analyst BI" ou autre

### 4. GenerationAgent

**Rôle:** Générer CV, lettre, email  
**Input:** analysis + positioning + profile_blocks  
**Process:**
1. Génère le contenu avec OpenAI (contextualisé par positioning)
2. Charge template Jinja2
3. Remplit variables: nom, skills, expérience, keywords
4. Vérifie pas d'invention (QualityAgent)
5. Enregistre en DB + fichier

**Output:** CV HTML, Lettre HTML, Email TXT

### 5. QualityAgent

**Rôle:** Vérifier que rien n'est inventé  
**Input:** Documents générés + profile_blocks  
**Process:**
1. Analyse chaque claim dans les docs
2. Vérifie que chaque skill/expérience existe dans profil
3. Détecte hallucinations

**Output:** "SAFE" / "REVIEW" / "REJECT"

### 6. EleviaAgent (⭐ NEW)

**Rôle:** Intégrer offres Elevia  
**Input:** Requête utilisateur ou ID offre  
**Process:**
1. Appelle API Elevia (offres du marché)
2. Retourne offres avec enrichissement

**Output:** Liste offres avec: id, title, company, url, match_score

---

## 🌐 Services (Infrastructure)

### openai_service.py

```python
async def analyze_offer(prompt: str) -> dict:
    """Appelle OpenAI API en JSON mode"""
    response = await client.chat.completions.create(
        model="gpt-4",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)
```

### application_service.py

```python
def create_application(db, user_id, offer_text, source_url=None):
    """CRUD pour applications"""
    app = Application(
        telegram_user_id=user_id,
        raw_offer=offer_text,
        source_url=source_url
    )
    db.add(app)
    db.commit()
    return app

def save_analysis(db, app_id, analysis):
    """Enregistre analyse JSON"""
    job_analysis = JobAnalysis(
        application_id=app_id,
        analysis_json=analysis
    )
    db.add(job_analysis)
    db.commit()

def save_document(db, app_id, doc_type, content):
    """Enregistre CV/lettre/mail"""
    filepath = f"/outputs/app_{app_id}_{doc_type}.html"
    with open(filepath, 'w') as f:
        f.write(content)
    
    doc = GeneratedDocument(
        application_id=app_id,
        document_type=doc_type,
        content=content,
        file_path=filepath
    )
    db.add(doc)
    db.commit()
```

### document_service.py

```python
def render_cv(context: dict) -> str:
    """Remplit template CV avec données"""
    template = load_template("cv.html")
    return template.render(**context)
```

### scraping_service.py

```python
def extract_from_url(url: str) -> str:
    """Extrait texte offre depuis URL"""
    response = requests.get(url)
    text = trafilatura.extract(response.text)
    return text
```

### elevia_client.py (⭐ NEW)

```python
async def get_offers_catalog(limit: int = 20) -> dict:
    """Récupère offres depuis API Elevia"""
    response = await httpx.get(
        f"{self.base_url}/v1/offers",
        params={"limit": limit},
        headers={"Authorization": f"Bearer {self.api_key}"}
    )
    return response.json()
```

### bot_instance_manager.py (⭐ NEW)

```python
class BotInstanceManager:
    @staticmethod
    def acquire_lock():
        """Singleton lock - tue ancienne instance"""
        if PID_FILE.exists():
            old_pid = int(PID_FILE.read_text())
            os.kill(old_pid, signal.SIGTERM)  # Tue l'ancienne
        
        PID_FILE.write_text(str(os.getpid()))  # Écrit nouveau PID
```

### conversation_history_service.py (⭐ NEW)

```python
class ConversationHistoryService:
    @staticmethod
    def record_user_message(db, user_id, text, command=None):
        """Enregistre message utilisateur"""
        history = ConversationHistory(
            user_id=user_id,
            message_type="user_message",
            content=text,
            metadata={"command": command}
        )
        db.add(history)
        db.commit()
```

---

## 📱 Telegram Handlers (Interface)

**Fichier:** `app/bot/handlers.py` (1327 lignes)

### Command Handlers

```
/start            → Main menu
/help             → Aide
/last             → Dernière candidature
/intelligence     → Career intelligence
/gaps             → Skill gaps analysis
/projects         → Project recommendations
```

### Message Handlers

```
"Text message"    → handle_offer()    (analyse texte)
"CV text"         → handle_offer()
"URL"             → Extraction + analyse
"GO/CV/LETTRE/MAIL" → handle_command() (shortcuts)
```

### Callback Handlers (Boutons)

```
home                      → Main menu
analyze_offer             → Analyse offre
my_applications           → Liste candidatures
view_master_cv            → Affiche CV master
gen_cv:123                → Génère CV pour app 123
gen_letter:123            → Génère lettre
gen_mail:123              → Génère mail
gen_all:123               → Génère tous les docs
regenerate:123            → Régénère (nouvel angle)
save_application:123      → Sauvegarde
intelligence_menu         → Ouvre agent IA
```

### Intelligence Handlers (⭐ NEW)

```python
ConversationHandler:
  - Entry point: intelligence_menu
  - States:
    INTELLIGENCE_MENU       → Affiche options (companies, locations, skills, etc)
    ASKING_QUESTION         → Utilisateur pose une question libre
  - Callbacks:
    intel_companies         → Affiche top companies du marché
    intel_back              → Retour à menu
    intel_...              → Autres insights
```

---

## 🔌 Elevia Integration (⭐ NEW)

### Commands

```
/elevia_health           → Check API status
/search_offers <query>   → Cherche offres (ex: "data scientist Spain")
/catalog [page]          → Browse offres
/load_elevia_offer <id>  → Charge offre → analyse complet
/upload_profile          → Upload CV pour matching
/get_profile             → Affiche profil analysé
```

### Flow Complet

```
User: /search_offers senior python france
    ↓
elevia_search_offers()
    ↓
EleviaAgent.search_offers("senior python france")
    ↓
EleviaClient → HTTP GET /api/v1/offers?q=...
    ↓
Elevia API returns: [{ id, title, company, location, url }, ...]
    ↓
Format response + show to Telegram
    ↓
User clicks offer ID
    ↓
/load_elevia_offer <id>
    ↓
elevia_load_offer()
    ↓
EleviaAgent.get_offer_detail(id)
    ↓
Create Application + Analyze (SAME PIPELINE AS URL/TEXT)
    ↓
Show analysis with buttons (Générer, Sauvegarder)
```

---

## 🔒 Deployment (Nouvelle Architecture)

### Avant (Polling)

```
Telegram API
    ↓
Bot.run_polling()
    ↓
Conflict if 2 instances! ❌
```

### Maintenant (Polling + Singleton)

```
Telegram API
    ↓
Bot starts
    ↓
BotInstanceManager.acquire_lock()
    ├─ Old instance running? → Kill it
    └─ Write new PID
    ↓
Bot.run_polling() (safe, only 1 instance)
```

### Future (Webhooks)

```
Telegram API
    ↓
Sends POST to webhook URL
    ↓
FastAPI server
    ↓
app.run() (no polling needed)
    ↓
Zero conflicts, <100ms latency ✅
```

---

## 📋 Request Flow Complet

```
1. USER INTERACTION
   👤 Utilisateur Telegram
   └─ Envoie offre ou clique bouton

2. BOT RECEIVES
   📡 telegram.ext.Application.run_polling()
   └─ Reçoit Update object

3. HANDLERS ROUTE
   🔀 app/bot/handlers.py
   ├─ CommandHandler("start") → start_command()
   ├─ MessageHandler(TEXT) → handle_offer()
   └─ CallbackQueryHandler("gen_all") → gen_all_callback()

4. AGENTS PROCESS
   🤖 app/agents/
   ├─ AnalysisAgent.analyze(offer_text)
   ├─ MatchingAgent.enrich_analysis()
   ├─ PositioningAgent.choose_angle()
   └─ GenerationAgent.generate_documents()

5. SERVICES EXECUTE
   ⚙️ app/services/
   ├─ openai_service.analyze_offer()
   ├─ application_service.save_analysis()
   ├─ document_service.render_cv()
   └─ elevia_client.get_offers()

6. DATABASE STORES
   💾 PostgreSQL
   ├─ INSERT applications
   ├─ INSERT job_analysis
   ├─ INSERT generated_documents
   └─ UPDATE user_sessions

7. BOT RESPONDS
   💬 Telegram API
   └─ update.message.reply_text() ou edit_message_text()

8. HISTORY RECORDED
   📝 conversation_history
   └─ record_user_message() / record_bot_reply()
```

---

## 🎯 Résumé des Étapes

| # | Étape | Composant | Résultat |
|---|-------|-----------|----------|
| 1 | Utilisateur envoie offre | Bot/Handlers | Message reçu |
| 2 | Extraction texte | scraping_service | Texte brut |
| 3 | Analyse offre | AnalysisAgent → OpenAI | JSON analysis |
| 4 | Validation profil | MatchingAgent → DB | Skills match score |
| 5 | Choix angle | PositioningAgent → OpenAI | "Data Analyst BI" |
| 6 | Génération docs | GenerationAgent + Templates | CV/Letter/Mail |
| 7 | Vérification qualité | QualityAgent → OpenAI | "SAFE" ou "REVIEW" |
| 8 | Sauvegarde BD | application_service | Tout enregistré |
| 9 | Affichage bot | Telegram API | Réponse utilisateur |
| 10 | Historique | conversation_history_service | Audit trail |

---

## 🚀 Technologies Utilisées

- **Python 3.11** - Langage
- **FastAPI** - Web server (optionnel, webhooks)
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **python-telegram-bot** - Telegram API wrapper
- **OpenAI API** - LLM (analyse, génération)
- **Jinja2** - Template rendering
- **Trafilatura** - Web scraping
- **httpx** - HTTP client async
- **Alembic** - Database migrations

---

**Status:** ✅ Production-ready (MVP v1.1 avec Elevia + Histoire)  
**Next:** Option A (actuel) ou Option B (webhooks)
