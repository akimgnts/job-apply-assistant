# Full Code Audit — Job Apply Assistant

**Date:** 2026-06-14  
**Status:** Production (v1.0)  
**Codebase State:** Functional but with critical hallucination risks

---

## 1. Vue d'ensemble du projet

**Job Apply Assistant** est un assistant IA accessible via Telegram qui analyse les offres d'emploi et génère automatiquement des documents candidature personnalisés (CV, lettre de motivation, email).

### Flux utilisateur principal:
1. L'utilisateur envoie une offre d'emploi (URL ou texte)
2. Le système analyse l'offre et la compare au profil candidat
3. Une stratégie de positionnement est proposée
4. L'utilisateur peut demander CV + lettre + email
5. Les documents sont générés et envoyés via Telegram

### Principes architecturaux déclarés:
- ✅ **Agents isolés**: Business logic indépendante de Telegram
- ✅ **Services découplés**: OpenAI, DB, fichiers séparés
- ✅ **Pas d'invention**: Seul le contenu des profile_blocks peut être utilisé
- ⚠️ **Vérité source unique**: profile_blocks = la source de vérité

**État réel:** Les principes sont déclarés mais partiellement appliqués.

---

## 2. Architecture globale

```
┌─────────────┐
│   Telegram  │ ◄─── Utilisateur envoie offre / commande
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│ app/bot/handlers.py                                 │
│ • handle_offer() → détecte URL/texte, crée application
│ • handle_command() → CV/LETTRE/MAIL/GO             │
│ • start_command(), help_command(), last_command()  │
└──────┬──────────────────────────────────────────────┘
       │
       ├─────────────────────────────────────────────────────────┐
       │                                                         │
       ▼                                                         ▼
┌──────────────────────────────┐         ┌───────────────────────────────┐
│ app/agents/                  │         │ app/services/                 │
│ • InputAgent.process()       │         │ • openai_service             │
│ • AnalysisAgent.analyze()    │ ───────▶ • scraping_service           │
│ • MatchingAgent.enrich()     │         │ • application_service        │
│ • PositioningAgent.choose()  │         │ • document_service           │
│ • GenerationAgent.generate() │         │ • debug utilities            │
│ • QualityAgent.check()       │         └───────────────────────────────┘
└──────────────────────────────┘                     │
       │                                              │
       │                                              ▼
       │                                  ┌──────────────────────────┐
       │                                  │ OpenAI API              │
       │                                  │ (analyze, generate)      │
       │                                  └──────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ PostgreSQL Database              │
│ • profile_blocks (candidat)      │
│ • applications (offres)          │
│ • job_analyses (analyses)        │
│ • generated_documents (fichiers) │
│ • user_sessions (état utilisateur)
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ app/templates/                   │
│ • cv.html (Jinja2)              │
│ • letter.html (Jinja2)          │
│ • mail.txt (Jinja2)             │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ outputs/                         │
│ • app_X_cv.html                 │
│ • app_X_letter.html             │
│ • app_X_mail.txt                │
└──────┬───────────────────────────┘
       │
       ▼
    ┌─────────────┐
    │   Telegram  │ ◄─── Documents envoyés à l'utilisateur
    └─────────────┘
```

---

## 3. Arborescence commentée

### `app/bot/`
**Rôle:** Interface Telegram. Seul point d'entrée utilisateur.

- `telegram_bot.py` — Setup polling, enregistrement des handlers
- `handlers.py` — Logique des commandes (réception → agents → réponse)

**Dépendances:** Agents, services, DB  
**Responsabilité:** Orchestration uniquement, pas de logique métier

### `app/agents/`
**Rôle:** Business logic pure, indépendant du framework.

- `input_agent.py` — Détecte URL vs texte, extrait contenu
- `analysis_agent.py` — Appelle OpenAI pour analyser l'offre
- `matching_agent.py` — Valide bloc IDs, enrichit analyse
- `positioning_agent.py` — Choisit angle candidature parmi 7 options fixes
- `generation_agent.py` — Génère CV/lettre/email via OpenAI + Jinja2
- `quality_agent.py` — (non utilisé dans handlers) Vérifie hallucinations

**Dépendances:** Services, DB, prompts  
**Responsabilité:** Traitement pur, appels OpenAI, pas de Telegram

### `app/services/`
**Rôle:** Infrastructure et intégrations externes.

- `openai_service.py` — Wrapper OpenAI avec json_mode support
- `scraping_service.py` — Extraction texte d'URL (trafilatura)
- `document_service.py` — Rendu Jinja2, sauvegarde fichiers
- `application_service.py` — Toutes les opérations DB (CRUD)

**Dépendances:** Config, models  
**Responsabilité:** Externe APIs et I/O, pas de logic métier

### `app/database/`
**Rôle:** Persistance et modèles de données.

- `models.py` — SQLAlchemy ORM (5 tables)
- `db.py` — Connection, SessionLocal factory
- `seed_profile.py` — Script d'initialisation profile_blocks
- `migrations/` — Alembic versioning

**Dépendances:** Config  
**Responsabilité:** État persistant unique

### `app/prompts/`
**Rôle:** Templating IA (une couche d'indirection pour prompts).

- `analysis_prompt.py` — Job analysis
- `positioning_prompt.py` — Angle selection (7 options)
- `generation_prompt.py` — CV/lettre/mail generation
- `quality_prompt.py` — Hallucination detection (not used)

**Format:** Fonctions retournant strings (pas d'objets)  
**Risque:** Prompts trop permissifs

### `app/templates/`
**Rôle:** Présentation finale (Jinja2).

- `cv.html` — Template CV professionnel
- `letter.html` — Template lettre motivation
- `mail.txt` — Template email recruiteur

**Format:** Jinja2 avec variables structurées  
**Responsabilité:** HTML only, pas de logique

### `app/utils/`
**Rôle:** Utilitaires transversaux.

- `debug.py` — Masquage secrets, formatting erreurs Telegram

### `migrations/`
**Rôle:** Versioning schéma DB.

Utilise Alembic pour migrations auto-générées.

### `outputs/`
**Rôle:** Fichiers générés temporaires.

Stocke HTML/TXT avant envoi Telegram.
Non commité (dans .gitignore).

---

## 4. Audit fichier par fichier

### `app/config.py`
**Chemin:** `app/config.py`

**Rôle:**  
Centralise configuration depuis variables env. Source unique pour secrets, chemins, flags.

**Classe principale:**
- `Config` — Stateful singleton

**Entrées:**
- Env vars: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `CANDIDATE_*`, `DEBUG_TELEGRAM_ERRORS`
- Fichier: `.env`

**Sorties:**
- Objet `config` (global)

**Dépendances:**
- `python-dotenv`
- `pathlib`

**Sources de données:**
- `.env` file
- OS environment

**Tables DB:** Aucune lecture

**Appels OpenAI:** Aucun

**Risques:**
- ⚠️ Env vars `CANDIDATE_NAME` etc. peuvent être vides → fallback à empty string (bon)
- ⚠️ Pas de validation des valeurs (ex: `OPENAI_API_KEY` invalide ne cause erreur qu'à l'appel)

**Améliorations recommandées:**
- Validation stricte au démarrage (fail-fast)
- Docstrings pour chaque var env

---

### `app/bot/handlers.py`
**Chemin:** `app/bot/handlers.py`

**Rôle:**  
Interface utilisateur Telegram. Reçoit messages, appelle agents, envoie réponses. Gère exceptions.

**Fonctions principales:**
- `start_command()` — Message de bienvenue
- `help_command()` — Aide détaillée
- `last_command()` — Dernière application
- `handle_offer()` — Traitement offre (URL/texte)
- `handle_command()` — GO/CV/LETTRE/MAIL
- `format_analysis_summary()` — Formatage analyse

**Entrées:**
- `Update` (message Telegram)
- `ContextTypes` (bot context)

**Sorties:**
- Messages Telegram texte/document

**Dépendances:**
- Tous les agents
- `application_service`
- `document_service` (pour debug)
- `debug utilities`

**Sources de données:**
- DB (via SessionLocal)
- Telegram message
- Agents (analysis, positioning, generation)

**Tables DB lues:**
- `profile_blocks` (via agents)
- `applications` (get_last_application)
- `job_analyses` (app.analyses)
- `user_sessions` (update_user_session)

**Tables DB écrites:**
- `applications` (create)
- `job_analyses` (save)
- `generated_documents` (save)
- `user_sessions` (update)

**Appels OpenAI:**
- Via `AnalysisAgent.analyze()` → 1 appel JSON
- Via `PositioningAgent.choose_angle()` → 1 appel texte
- Via `GenerationAgent.generate_cv/letter/mail()` → 1-3 appels JSON

**Risques:**
- ⚠️ Exception handling envoie messages bruts à l'utilisateur
- ✅ Nouveau: Si `DEBUG_TELEGRAM_ERRORS=true`, envoie stack traces maskées
- ⚠️ Session DB non fermée en cas d'exception critique (finally bloc existe mais erreurs avant)
- ⚠️ Pas de timeout sur appels OpenAI (peuvent bloquer longtemps)

**Améliorations recommandées:**
- Ajouter timeouts OpenAI (max 30s)
- Améliorer gestion des sessions (context manager)
- Ajouter rate limiting par utilisateur

---

### `app/agents/input_agent.py`
**Chemin:** `app/agents/input_agent.py`

**Rôle:**  
Détecte si input est URL ou texte. Extrait contenu d'URL.

**Fonction principale:**
- `process(raw_input: str) → (offer_text, metadata)`

**Entrées:**
- `raw_input` — texte brut (URL ou texte)

**Sorties:**
- `offer_text` — contenu extrait (ou None si URL invalide)
- `metadata` — dict avec `is_url`, `source_url`, `raw_length`

**Dépendances:**
- `scraping_service.process_input()`

**Sources de données:**
- Web (si URL, via trafilatura)

**Tables DB:** Aucune

**Appels OpenAI:** Aucun

**Risques:**
- ✅ Retourne None si URL fails → handlers redirige utilisateur vers texte brut (bon)
- ⚠️ URL extraction timeout possible (trafilatura peut être lent)
- ⚠️ Pas de limite taille résultats (texte très long possible)

**Améliorations:**
- Ajouter timeout trafilatura (5s)
- Limiter taille résultats à 50KB

---

### `app/agents/analysis_agent.py`
**Chemin:** `app/agents/analysis_agent.py`

**Rôle:**  
Analyse l'offre d'emploi et match avec le profil candidat. Appel IA principal.

**Fonction principale:**
- `analyze(db: Session, job_offer: str) → dict`

**Entrées:**
- `job_offer` — texte brut de l'offre
- DB connection

**Sorties:**
- Dict JSON:
  ```json
  {
    "company": "...",
    "job_title": "...",
    "required_skills": [...],
    "ats_keywords": [...],
    "match_score": 0-10,
    "strengths": [...],
    "missing_points": [...],
    "cv_strategy": "...",
    "profile_blocks_to_use": [ids],
    "profile_blocks_to_avoid": [ids],
    "risk_of_overclaiming": [...]
  }
  ```

**Dépendances:**
- `openai_service.analyze_offer()` (JSON mode)
- `analysis_prompt.get_analysis_prompt()`
- DB for profile_blocks

**Sources de données:**
- `profile_blocks` table (ALL blocks, ordered by priority DESC)
- `job_offer` param

**Tables DB lues:**
- `profile_blocks` (tous)

**Tables DB écrites:** Aucune (sauvé ailleurs)

**Appels OpenAI:**
- 1 appel JSON avec profile + offer
- Modèle: `gpt-4o-mini`
- Timeout: inhérent OpenAI SDK

**Risques:**
- 🔴 **CRITIQUE:** Prompt dit "Candidate can ONLY use what exists" mais ne valide rien en retour
- 🔴 **CRITIQUE:** OpenAI reçoit TOUT le profil, peut inventer combinations non existantes
- ⚠️ `profile_blocks_to_use` retournées par IA (IA choisit blocks) → pas de validation post-hoc
- ⚠️ `missing_points` générée par IA (peut être inexacte)

**Exemple d'hallucination:**
```
Profile blocks: [
  { id: 1, title: "Python", category: "skill" },
  { id: 2, title: "Data Analysis", category: "skill" }
]

Offre: "Seeking Master's degree in Data Science"

AI peut retourner:
{
  "missing_points": ["Master's in Data Science"],
  "profile_blocks_to_use": [1, 2]
}
✅ Correct

MAIS: rien n'empêche AI de :
{
  "company": "TechCorp Inc",  # ← pas dans profile
  "required_skills": [
    "Python" (OK),
    "R" (OK),
    "Advanced ML" (OK),
    "Kubernetes" (NOT in profile!),  # ← hallucination
    "AWS" (NOT in profile!)
  ]
}
```

**Améliorations recommandées:**
- ✅ Validation stricte `profile_blocks_to_use` (MatchingAgent fait déjà ça)
- ❌ Validation POST-IA: checker que `missing_points` ne contiennent pas infos du profil
- ❌ Ajouter `only_candidates_with_these_skills` au prompt pour restreindre

---

### `app/agents/matching_agent.py`
**Chemin:** `app/agents/matching_agent.py`

**Rôle:**  
Valide que blocks IDs retournés par IA existent. Enrichit analyse.

**Fonctions principales:**
- `enrich_analysis()` — Valide bloc IDs, filtre invalides
- `get_selected_blocks()` — Récupère contenu blocks sélectionnés

**Entrées:**
- `analysis` dict (de AnalysisAgent)
- DB connection

**Sorties:**
- `analysis` enrichie avec blocks valides

**Dépendances:**
- DB pour profile_blocks

**Sources de données:**
- `profile_blocks` table

**Tables DB lues:**
- `profile_blocks`

**Tables DB écrites:** Aucune

**Appels OpenAI:** Aucun

**Risques:**
- ✅ Valide bloc IDs (bon)
- ⚠️ Silencieusement filtre IDs invalides (AI peut ignorer cette validation et inventer dans génération)

**Améliorations:**
- Loguer si IA a retourné des IDs invalides (suspect)

---

### `app/agents/positioning_agent.py`
**Chemin:** `app/agents/positioning_agent.py`

**Rôle:**  
Choisit angle candidature (positioning) parmi liste fixe.

**Fonction principale:**
- `choose_angle(analysis: dict) → str`

**Entrées:**
- `analysis` dict

**Sorties:**
- Une string: `"Data Analyst BI"`, `"Marketing Data Analyst"`, etc. (7 options fixes)

**VALID_ANGLES:**
```python
[
  "Data Analyst BI",
  "Marketing Data Analyst",
  "Data & AI Project Analyst",
  "Automation / AI Workflow Analyst",
  "Data Steward / Data Quality",
  "Business Analyst orienté data",
  "Product / Ops Analyst",
]
```

**Dépendances:**
- `openai_service.generate_text()`
- `positioning_prompt.get_positioning_prompt()`

**Sources de données:**
- `analysis` (contexte pour choix)
- VALID_ANGLES (liste fixe)

**Tables DB:** Aucune

**Appels OpenAI:**
- 1 appel texte simple
- Fallback robuste (si IA retourne invalide, utilise `VALID_ANGLES[0]`)

**Risques:**
- ✅ Bonne stratégie: list fixe + fallback
- ⚠️ Prompt pourrait être plus contraint (force réponse à être exactement un des 7)

**Améliorations:**
- Ajouter "Must choose from: ..." strictement dans prompt

---

### `app/agents/generation_agent.py`
**Chemin:** `app/agents/generation_agent.py`

**Rôle:**  
Génère CV, lettre, email avec contenu structuré. **CRITÈRE DE QUALITÉ PRINCIPAL.**

**Fonctions principales:**
- `generate_cv()` — JSON payload → Jinja2 → HTML
- `generate_letter()` — Texte libre → HTML
- `generate_mail()` — Texte libre → TXT
- `generate_documents()` — Wrapper pour 1+ types
- `_clean_text()` — Enlève markdown/HTML
- `_clean_payload()` — Valide tout le payload

**Entrées:**
- DB connection
- `application_id` (int)
- `analysis` dict (de MatchingAgent)
- `positioning` str (de PositioningAgent)
- `document_types` list (["cv", "letter", "mail"])

**Sorties:**
- HTML ou TXT content (sauvé en DB + fichier)

**Dépendances:**
- `openai_service.generate_cv_payload()` (JSON mode)
- `openai_service.generate_text()` (texte libre)
- `generation_prompt.get_cv_payload_prompt()` etc.
- `MatchingAgent.get_selected_blocks()`
- `document_service.render_*()`, `save_document()`
- DB for save

**Sources de données:**
- Profile blocks (via MatchingAgent)
- Analysis (metadata)
- Config (candidate info)

**Tables DB lues:**
- `profile_blocks`

**Tables DB écrites:**
- `generated_documents` (save)

**Appels OpenAI:**
- CV: 1 appel JSON
- Lettre: 1 appel texte
- Mail: 1 appel texte

**Risques - CV Generation:**
- 🔴 **Critique avant fix:** Ancien code retournait HTML, template attendait structure JSON (mismatch)
- ✅ **Fix appliqué:** Nouveau prompt `get_cv_payload_prompt()` retourne JSON structuré
- ✅ `_clean_text()` enlève markdown/HTML
- ✅ `_clean_payload()` valide tout

**Risques - Lettre & Mail:**
- ⚠️ Pas de JSON mode (retourne texte libre)
- ⚠️ Pas de validation (contenu IA accepté tel quel)
- ⚠️ Risque: IA peut inventer certifications, expériences, entreprises
- 📝 Exemple: "Worked at Google on ML projects" ← peut ne pas exister

**Risques - Candidate Info:**
- ✅ Fallback à empty string (pas "Candidate")
- ⚠️ Si `CANDIDATE_NAME` vide, CV affiche "Candidate" vide (template gère)

**Améliorations recommandées:**
- Lettre/mail: Ajouter JSON mode avec validation
- Tous: Post-générations, vérifier aucune phrase ne contient infos non dans blocks

---

### `app/agents/quality_agent.py`
**Chemin:** `app/agents/quality_agent.py`

**Rôle:**  
Vérifier documents générés ne contiennent pas hallucinations. **Non utilisé dans handlers.**

**Fonction principale:**
- `check_document(db, document_content, document_type) → dict`

**Entrées:**
- Document HTML/TXT généré
- Type de document

**Sorties:**
- Report:
  ```json
  {
    "quality_score": 0-10,
    "recommendation": "SAFE|REVIEW|REJECT",
    "issues": [...]
  }
  ```

**Dépendances:**
- `openai_service.analyze_offer()` (JSON)
- `quality_prompt.get_quality_check_prompt()`
- DB for profile_blocks

**Sources de données:**
- Document content (HTML/TXT)
- Profile blocks

**Tables DB lues:**
- `profile_blocks`

**Tables DB écrites:** Aucune

**Appels OpenAI:**
- 1 appel JSON

**Risques:**
- 🔴 **Pas utilisé en production** — handlers n'appellent jamais QualityAgent
- ⚠️ Même si utilisé, IA peut répondre incorrectement ("looks good" sur hallucination)

**État:**
- Code fonctionnel mais dead code
- Suggestion: Ajouter `/audit_document` command pour tester manuellement

---

### `app/services/openai_service.py`
**Chemin:** `app/services/openai_service.py`

**Rôle:**  
Wrapper OpenAI. Gère modes JSON/texte, error handling.

**Fonctions principales:**
- `call_openai()` — Call basique (+ json_mode flag)
- `analyze_offer()` — JSON mode (pour analyses)
- `generate_text()` — Texte libre (pour générations)
- `generate_cv_payload()` — JSON mode (nouveau, pour CV)

**Entrées:**
- `prompt` string
- `json_mode` bool

**Sorties:**
- String (texte brut ou JSON)

**Dépendances:**
- `openai` SDK
- Config (API key, model)

**Sources de données:**
- OpenAI API

**Appels OpenAI:**
- Tous passent par ici

**Risques:**
- ⚠️ Pas de rate limiting
- ⚠️ Pas de retry logic (fail immédiat)
- ⚠️ API key en config (ok, vient d'env)
- ⚠️ Modèle dur-codé `gpt-4o-mini` (bon pour coûts)

**Améliorations:**
- Ajouter retry avec backoff exponentiel
- Ajouter rate limiter par utilisateur
- Ajouter timeout (30s)

---

### `app/services/scraping_service.py`
**Chemin:** `app/services/scraping_service.py`

**Rôle:**  
Extrait texte d'URLs, détecte URL vs texte brut.

**Fonctions principales:**
- `is_url()` — Check URL valide
- `extract_from_url()` — Trafilatura
- `process_input()` — Orchestration

**Entrées:**
- `raw_input` string

**Sorties:**
- `(offer_text, is_url, source_url)`

**Dépendances:**
- `trafilatura` (web scraping)
- `urllib.parse`

**Sources de données:**
- Web (URLs)

**Appels OpenAI:** Aucun

**Risques:**
- ⚠️ Trafilatura peut être lent (pas de timeout)
- ⚠️ URL extraction peut fail silencieusement (retourne empty string, pas erreur)
- ⚠️ Pas de validation "ce n'est pas un job posting" (n'importe quel URL accepté)

**Améliorations:**
- Ajouter timeout trafilatura (5s)
- Valider que texte extrait contient mots-clés "job", "position", "role", etc.

---

### `app/services/application_service.py`
**Chemin:** `app/services/application_service.py`

**Rôle:**  
Toutes les opérations DB (CRUD). Source unique pour data access.

**Fonctions principales:**
- `create_application()` — Crée application
- `save_analysis()` — Sauvegarde analyse JSON
- `update_application_with_analysis()` — Maj après analyse
- `get_or_create_user_session()` — Gère user state
- `update_user_session()` — MAJ session
- `get_last_application()` — Récupère dernière app
- `mark_application_as_generated()` — MAJ status

**Entrées:**
- DB session
- IDs, dicts, strings

**Sorties:**
- SQLAlchemy objects

**Dépendances:**
- SQLAlchemy ORM
- Models

**Tables DB lues/écrites:**
- applications (all ops)
- job_analyses (all ops)
- user_sessions (all ops)
- generated_documents (via handlers, pas via ce service)

**Appels OpenAI:** Aucun

**Risques:**
- ✅ Bonne séparation: tous les DB ops ici
- ⚠️ Pas de transactions (chaque save est commit individuel)
- ⚠️ Pas de audit trail (qui a changé quoi, quand)

**Améliorations:**
- Ajouter transactions pour operateurs multi-étapes
- Ajouter `updated_by`, `updated_at` systématiquement

---

### `app/services/document_service.py`
**Chemin:** `app/services/document_service.py`

**Rôle:**  
Rendu Jinja2, sauvegarde fichiers, debug info.

**Fonctions principales:**
- `render_cv()` → HTML
- `render_letter()` → HTML
- `render_mail()` → TXT
- `save_document()` → Fichier
- `get_output_path()` → Chemin fichier
- `get_template_debug_info()` → Debug

**Entrées:**
- Context dict (variables Jinja)
- Application ID, document type

**Sorties:**
- HTML/TXT string
- Fichier sauvegardé

**Dépendances:**
- Jinja2
- Pathlib
- Templates (fichiers)

**Sources de données:**
- Templates (fichiers locaux)

**Appels OpenAI:** Aucun

**Risques:**
- ✅ Fix appliqué: Paths maintenant absolus (fonctionne en Docker)
- ✅ Templates trouvés avec `Path(__file__).resolve()`
- ⚠️ Pas de validation contexte (si key manquante, Jinja erreur)
- ⚠️ Pas de vérification taille fichier (HTML peut être très gros)

**Améliorations:**
- Valider context keys minimales avant render
- Limiter taille HTML générés (max 5MB)

---

### `app/utils/debug.py`
**Chemin:** `app/utils/debug.py`

**Rôle:**  
Masquage secrets, formatting erreurs pour Telegram.

**Fonctions principales:**
- `mask_secrets()` — Remplace credentials
- `format_exception_for_telegram()` — Pretty-print erreurs
- `split_telegram_message()` — Gère limite 4096 chars

**Entrées:**
- Exception, context dict, debug dict

**Sorties:**
- String masquée prête pour Telegram

**Dépendances:**
- `re` (regex)
- `traceback`

**Appels OpenAI:** Aucun

**Risques:**
- ✅ Masque OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, DATABASE_URL passwords
- ✅ Masque sk-proj-* tokens OpenAI
- ✅ Masque postgres://user:pass@ patterns
- ⚠️ Regex peut miss edge cases (ex: secrets non entre ``/`` ?)
- ✅ Message split à 3500 chars (safe pour Telegram)

**Améliorations:**
- Ajouter test cases pour tous les secret patterns
- Ajouter redaction markers (ex: `sk-proj-[REDACTED]` au lieu de `***MASKED***`)

---

### `app/database/models.py`
**Chemin:** `app/database/models.py`

**Rôle:**  
ORM SQLAlchemy. Définie 5 tables.

**Tables & colonnes:**

#### ProfileBlock
```python
id: int (PK)
category: CategoryEnum (experience|skill|project|education|certification|tool|language)
title: str (255)
content: text (long)
tags: JSON (list, ex: ["Python", "3+ years"])
truth_level: TruthLevelEnum (verified|project|in_progress|learning)
priority: int (0-10, higher = more relevant)
created_at, updated_at: datetime
```

**Rôle:** Vérité source du profil candidat. Jamais modifié via bot.

#### Application
```python
id: int (PK)
telegram_user_id: str (255)
company: str (255, nullable)
job_title: str (255, nullable)
source_url: text (nullable)
raw_offer: text (mandatory)
recommended_angle: str (255, nullable)
match_score: int (nullable, 0-10)
status: ApplicationStatusEnum (analyzed|generated|archived)
created_at, updated_at: datetime
```

**Rôle:** Chaque analyse d'offre. FK vers user via telegram_user_id.

#### JobAnalysis
```python
id: int (PK)
application_id: int (FK)
analysis_json: JSON (dict complet)
missions: JSON (list)
required_skills: JSON (list)
soft_skills: JSON (list)
ats_keywords: JSON (list)
missing_points: JSON (list)
strengths: JSON (list)
created_at: datetime
```

**Rôle:** Analyse détaillée, sauvegardée de AnalysisAgent.

#### GeneratedDocument
```python
id: int (PK)
application_id: int (FK)
document_type: DocumentTypeEnum (cv|letter|mail)
filename: str (255)
content: text (HTML/TXT)
file_path: text (chemin local)
created_at: datetime
```

**Rôle:** Documents générés. Permet récupération ultérieure et audit.

#### UserSession
```python
id: int (PK)
telegram_user_id: str (255, unique)
last_application_id: int (FK, nullable)
state: str (50, ex: "waiting_for_command")
session_data: JSON (dict, ex: metadata)
created_at, updated_at: datetime
```

**Rôle:** État utilisateur. Permet multi-step workflow.

**Risques:**
- ⚠️ `raw_offer` jamais nettoyé (peut être 1MB+)
- ⚠️ `analysis_json` sauvegardé entièrement (peut contenir hallucinations)
- ✅ `generated_documents.content` sauvegardé (permet audit)
- ⚠️ Pas de soft delete (archived status existe mais pas utilisé)

**Améliorations:**
- Limiter taille `raw_offer` (max 100KB)
- Ajouter `deleted_at` pour soft delete
- Indexer `telegram_user_id` (requêtes fréquentes)

---

### `app/prompts/analysis_prompt.py`
**Chemin:** `app/prompts/analysis_prompt.py`

**Rôle:**  
Prompt pour job offer analysis. OpenAI retourne JSON.

**Données envoyées:**
- Offre complète (job_offer)
- TOUS les profile_blocks (titre + contenu)

**Format sortie attendu:**
```json
{
  "company": "str",
  "job_title": "str",
  "required_skills": ["array"],
  "ats_keywords": ["array"],
  "match_score": 0-10,
  "strengths": ["array"],
  "missing_points": ["array"],
  "cv_strategy": "str",
  "profile_blocks_to_use": [ids],
  "profile_blocks_to_avoid": [ids],
  "risk_of_overclaiming": ["array"]
}
```

**Risques:**
- 🔴 **CRITIQUE:** Prompt dit "Candidate can ONLY use what exists" MAIS:
  - OpenAI reçoit tous les blocks (peut les combiner librement)
  - Pas de validation que retourné `required_skills` sont dans profil
  - `missing_points` peut être hallucination (IA invente)
  
**Exemple:**
```
Profile: Python, SQL, Excel
Offre: R programmer needed

IA peut retourner:
missing_points: ["R", "Scala", "Functional Programming"]

Correct. MAIS IA peut aussi retourner:
required_skills: ["R", "Scala", "C++", "Kubernetes"]
risk_of_overclaiming: ["claiming advanced Kubernetes experience"]

❌ C++ et Kubernetes ne sont nulle part dans le profil
```

**Améliorations:**
- Expliciter dans prompt: "required_skills MUST be subset of: [list all]"
- Ou: Demander IA de retourner `required_skills_in_profile` et `required_skills_missing` séparement

---

### `app/prompts/generation_prompt.py`
**Chemin:** `app/prompts/generation_prompt.py`

**Rôle:**  
Prompts pour CV/lettre/mail generation.

**Fonction principale:**
- `get_cv_payload_prompt()` — **Nouvelle** (JSON mode)
- `get_cv_prompt()` — Ancienne (texte libre, pas utilisée)
- `get_letter_prompt()` — Lettre (texte libre)
- `get_mail_prompt()` — Mail (texte libre)

**CV Payload (JSON mode):**
```json
{
  "title": "Job-aligned title (max 8 words)",
  "summary": "Plain text, max 70 words",
  "experiences": [
    {
      "title": "str",
      "company": "str",
      "context": "str",
      "dates": "YYYY – YYYY",
      "bullets": ["str", "str"]
    }
  ],
  "projects": [...],
  "skills_sections": [...],
  "education": [...],
  "certifications": [...],
  "languages": [...],
  "ats_keywords": ["str", ...]
}
```

**Risques - CV:**
- ✅ JSON mode (strict)
- ✅ Prompt dit "Extract experiences/projects from CANDIDATE DATA, rewrite them"
- ⚠️ "Rewrite them" peut être hallucination (IA ajoute détails non présents)
- ⚠️ ATS keywords: "Must match job requirements" (mais pas limité au profil)

**Risques - Lettre:**
- 🔴 Texte libre, pas JSON
- 🔴 Pas de validation
- ⚠️ Prompt vague: "Never invent experience" (pas d'enforcement)
- ⚠️ Peut inventer: "Worked on ML pipelines at TechCorp" ← pas dans profile

**Risques - Mail:**
- 🔴 Texte libre, pas JSON
- 🔴 Pas de validation
- ⚠️ Court (120 words) = plus de risque d'hallucination dense

**Améliorations:**
- Lettre: Ajouter JSON mode avec stricte validation
- Mail: Ajouter JSON mode
- Tous: Demander IA de retourner `confidence_per_claim` (IA rate confiance)

---

### Autres prompts

**`positioning_prompt.py`:**
- ✅ Constrainé (7 options fixes)
- ✅ Fallback robuste
- ✅ Pas de hallucinations possibles

**`quality_prompt.py`:**
- ⚠️ Non utilisé (dead code)
- ⚠️ Même si utilisé, IA peut se tromper (relying sur IA pour vérifier IA)

---

### `app/templates/cv.html`
**Chemin:** `app/templates/cv.html`

**Rôle:**  
Rendu HTML CV. Jinja2 template. Reçoit contexte structuré.

**Contexte attendu:**
```json
{
  "candidate": {
    "name": "str",
    "email": "str",
    "phone": "str",
    "linkedin": "str",
    "github": "str",
    "website": "str"
  },
  "cv": {
    "title": "str",
    "summary": "str",
    "experiences": [...],
    "projects": [...],
    "skills_sections": [...],
    "education": [...],
    "certifications": [...],
    "languages": [...],
    "ats_keywords": ["str"]
  }
}
```

**Features:**
- ✅ Responsive (A4 page)
- ✅ Professional design (Manrope font, minimal)
- ✅ Print-friendly CSS
- ✅ Conditional sections ({% if ... %})
- ✅ Loops avec loop.index0, loop.last (Jinja native)

**Risques:**
- ✅ Fix appliqué: Remplacé `enumerate()` par `loop.index0`
- ⚠️ Pas de XSS protection (template assume data safe)

**Améliorations:**
- Ajouter `|safe` filters si needed (actuellement pas)
- Ajouter footnote avec disclaimer si candidate info incomplete

---

## 5. Audit du workflow Telegram

### Workflow: Utilisateur envoie offre

```
User (Telegram)
    │
    ├─ "https://example.com/job"
    └─ OR "Job description text..."
            │
            ▼
   handle_offer()
    │
    ├─ InputAgent.process()
    │  └─ scraping_service.process_input()
    │     └─ [URL? extract] OR [keep text]
    │
    ├─ create_application(db, user_id, offer_text, url)
    │  └─ DB: INSERT applications
    │
    ├─ AnalysisAgent.analyze(db, offer_text)
    │  │
    │  ├─ ProfileBlocks.query(db)
    │  │  └─ DB: SELECT all profile_blocks
    │  │
    │  └─ openai_service.analyze_offer(prompt)
    │     └─ OpenAI (JSON mode)
    │        Returns: analysis_json
    │
    ├─ MatchingAgent.enrich_analysis(analysis, db)
    │  └─ Valide profile_blocks_to_use IDs
    │     (silencieusement filtre invalides)
    │
    ├─ save_analysis(db, app_id, analysis)
    │  └─ DB: INSERT job_analyses
    │
    ├─ update_application_with_analysis(db, app_id, analysis)
    │  └─ DB: UPDATE applications (company, job_title, score, status)
    │
    ├─ PositioningAgent.choose_angle(analysis)
    │  └─ openai_service.generate_text(prompt)
    │     └─ OpenAI (texte)
    │        Returns: angle (validé vs VALID_ANGLES)
    │
    ├─ update_user_session(db, user_id, app_id, state="waiting_for_command")
    │  └─ DB: INSERT/UPDATE user_sessions
    │
    └─ format_analysis_summary(analysis, angle)
       └─ Return message à Telegram
```

**État final:**
- ✅ Application créée (DB)
- ✅ Analysis sauvegardée (DB)
- ✅ User session maj (DB)
- ✅ Message Telegram: résumé + propositions

**Points de sortie:**
1. InputAgent.process() retourne None → user doit copier texte
2. AnalysisAgent.analyze() erreur → message "Error analyzing"
3. PositioningAgent erreur → fallback à VALID_ANGLES[0]

---

### Workflow: Utilisateur répond CV

```
User (Telegram): "CV"
    │
    ▼
handle_command(update, context)
    │
    ├─ get_last_application(db, user_id)
    │  └─ DB: SELECT user_sessions -> last_application_id
    │         SELECT applications WHERE id
    │
    ├─ app.analyses[0].analysis_json
    │  └─ Memory (déjà chargée)
    │
    ├─ GenerationAgent.generate_cv(
    │    db, app_id, analysis, positioning
    │  )
    │  │
    │  ├─ MatchingAgent.get_selected_blocks(db, block_ids)
    │  │  └─ DB: SELECT profile_blocks WHERE id IN (...)
    │  │
    │  ├─ get_cv_payload_prompt(analysis, blocks, positioning)
    │  │
    │  ├─ openai_service.generate_cv_payload(prompt)
    │  │  └─ OpenAI (JSON mode)
    │  │     Returns: cv_payload JSON
    │  │
    │  ├─ _clean_payload(payload)
    │  │  └─ Enlève markdown/HTML, valide structure
    │  │
    │  ├─ _build_candidate_info(db)
    │  │  └─ Config: CANDIDATE_NAME, EMAIL, etc.
    │  │
    │  ├─ render_cv(context)
    │  │  └─ Jinja2 template render
    │  │     Returns: HTML string
    │  │
    │  ├─ save_document(html, filepath)
    │  │  └─ Fichier: outputs/app_X_cv.html
    │  │
    │  └─ DB: INSERT generated_documents
    │         UPDATE applications status=generated
    │
    ├─ mark_application_as_generated(db, app_id)
    │  └─ DB: UPDATE applications
    │
    └─ Telegram: "✅ CV généré\n📄 CV"
       + send_document(cv.html)
```

**État final:**
- ✅ CV généré + sauvegardé (fichier + DB)
- ✅ Application marked as generated
- ✅ Document envoyé Telegram

**Points de sortie:**
1. Pas d'application trouvée → "No offer"
2. Analysis missing → "Analysis not found"
3. GenerationAgent erreur → message error + debug (si DEBUG_TELEGRAM_ERRORS=true)

---

### Workflow: Utilisateur répond GO

Même que CV, mais pour chaque type:
```
for doc_type in ["cv", "letter", "mail"]:
  GenerationAgent.generate_*(db, app_id, analysis, positioning)
  save_document()
  send_document(Telegram)
```

**Temps total:** ~15-30 secondes (3x OpenAI calls)

---

## 6. Audit de la base de données

### Table: profile_blocks

**Rôle:**  
Vérité source du profil candidat. Immutable en production.

**Colonnes:**
- `id` — Clé primaire
- `category` — Type (skill, experience, project, education, certification, tool, language)
- `title` — Titre/nom
- `content` — Description longue
- `tags` — JSON array (ex: ["Python", "3 years"])
- `truth_level` — verified, project, in_progress, learning
- `priority` — 0-10 (higher = plus relevant pour candidature)
- `created_at`, `updated_at`

**Qui écrit:**
- Seed script (initial)
- ❌ Pas modifiable via bot

**Qui lit:**
- AnalysisAgent (toutes les blocks)
- MatchingAgent (blocks sélectionnés)
- GenerationAgent (blocks sélectionnés)
- QualityAgent (pour validation)

**Exemple d'usage:**
```python
blocks = db.query(ProfileBlock).order_by(ProfileBlock.priority.desc()).all()
# [
#   { id: 1, title: "Python", category: "skill", priority: 10, ... },
#   { id: 2, title: "Data Analysis", category: "skill", priority: 9, ... },
#   { id: 3, title: "Sidel", category: "experience", priority: 8, ... }
# ]
```

**Risques:**
- ⚠️ Pas versionné (si modifié, ancienne analyse invalide)
- ⚠️ Pas de change tracking

---

### Table: applications

**Rôle:**  
Chaque offre traitée.

**Colonnes:**
- `id` — PK
- `telegram_user_id` — FK (string, pas int)
- `company`, `job_title` — Extraites de l'analyse
- `source_url` — URL originale (nullable)
- `raw_offer` — Texte complet de l'offre
- `recommended_angle` — Positioning choisi
- `match_score` — 0-10
- `status` — analyzed, generated, archived
- `created_at`, `updated_at`

**Qui écrit:**
- handlers.create_application()
- handlers.update_application_with_analysis()
- handlers.mark_application_as_generated()

**Qui lit:**
- get_last_application() (via user_sessions)
- GenerationAgent (pour app_id)

**Risques:**
- ⚠️ `raw_offer` peut être très gros (pas de limite)
- ⚠️ `telegram_user_id` = string (correct, pas d'UUID mapping)

---

### Table: job_analyses

**Rôle:**  
Analyse structurée retournée par OpenAI.

**Colonnes:**
- `id` — PK
- `application_id` — FK
- `analysis_json` — JSONB (dict entier)
- `missions`, `required_skills`, `soft_skills`, `ats_keywords`, `missing_points`, `strengths` — Arrays extraites

**Qui écrit:**
- handlers.save_analysis()

**Qui lit:**
- handlers.handle_command() (pour récupérer analysis)
- GenerationAgent (pour data)

**Risques:**
- ⚠️ Entièrement JSONB (pas validé, peut contenir hallucinations)
- ⚠️ Colonnes redondantes (analysis_json + décomposées)

---

### Table: generated_documents

**Rôle:**  
Audit trail des documents générés.

**Colonnes:**
- `id` — PK
- `application_id` — FK
- `document_type` — cv, letter, mail
- `filename` — ex: "app_7_cv.html"
- `content` — HTML/TXT complet
- `file_path` — chemin local
- `created_at`

**Qui écrit:**
- GenerationAgent.generate_cv/letter/mail()

**Qui lit:**
- handlers.handle_command() (pour envoyer Telegram)

**Risques:**
- ✅ Bonne: Sauvegarde contenu entièrement (permet audit)
- ⚠️ `content` peut être très gros (5MB+)

---

### Table: user_sessions

**Rôle:**  
État utilisateur (multi-step workflow support).

**Colonnes:**
- `id` — PK
- `telegram_user_id` — FK, unique
- `last_application_id` — FK, nullable
- `state` — "idle", "waiting_for_command", etc.
- `session_data` — JSONB (metadata)
- `created_at`, `updated_at`

**Qui écrit:**
- handlers.update_user_session()

**Qui lit:**
- handlers.handle_command() (pour get_last_application)

**Risques:**
- ✅ Bonne: State tracking
- ⚠️ `state` pas utilisé (toujours "waiting_for_command")

---

## 7. Audit des prompts IA

### Analysis Prompt

**Objectif:**  
Analyser offre d'emploi, matcher avec profil, retourner IDs de blocks à utiliser.

**Données envoyées:**
- Offre complète (texte)
- TOUS les profile_blocks (titre + contenu)

**Format sortie attendu:** JSON structuré

**Risques:**
- 🔴 CRITIQUE: IA reçoit tous les blocks, peut les combiner librement
- 🔴 Pas de validation que skills retournées sont dans profil

**Améliorations:**
- Expliciter: "required_skills MUST be exact matches from: [list]"
- Ou: Demander 2 listes séparées (in_profile, missing)

---

### Positioning Prompt

**Objectif:**  
Choisir angle candidature.

**Données envoyées:**
- Analysis metadata

**Format sortie:** Une string (7 options fixes)

**Risques:**
- ✅ Peu de risque (list fixe)

**Améliorations:**
- Forcer réponse à être exactement un des 7

---

### CV Payload Prompt

**Objectif:**  
Générer CV structuré (JSON). Rewrite profile blocks.

**Données envoyées:**
- Analysis
- Blocks sélectionnés (titre + contenu)
- Positioning

**Format sortie:** JSON structuré

**Risques:**
- ⚠️ "Rewrite them" = IA ajoute détails (hallucination possible)
- ⚠️ ATS keywords non limités au profil

**Améliorations:**
- Expliciter: "Bullets must use ONLY information from provided blocks"
- Limiter ATS keywords à: "Must be from job offer OR profile blocks"

---

### Letter & Mail Prompts

**Objectif:**  
Générer lettre/email texte libre.

**Données envoyées:**
- Analysis
- Positioning

**Format sortie:** Texte libre

**Risques:**
- 🔴 Pas de structure (texte libre)
- 🔴 Pas de validation
- ⚠️ Peut inventer expériences, certifications, entreprises
- 🔴 QualityAgent existe mais pas utilisé

**Améliorations:**
- Ajouter JSON mode (structurer)
- Ajouter validation stricte vs profile_blocks
- Ou: Requérir "Source de chaque affirmation" (citation tracking)

---

## 8. Audit du problème actuel: hallucination du CV

### Exemple observé:
CV généré contient:
- "Tech Solutions Inc." (pas dans profile_blocks)
- "Master's in Data Science" (pas dans profile_blocks)
- "Certified Data Analyst" (pas dans profile_blocks)

### Root cause analysis:

**Avant fix (ancien code):**
1. `generate_cv()` appelait `get_cv_prompt()` (demande HTML)
2. OpenAI retournait HTML/texte libre
3. Context passait HTML directement au template
4. Template attendait structure JSON ❌ Mismatch
5. Affichage cassé, données mélangées

**Current (après fix appliqué):**
1. `generate_cv()` appelle `get_cv_payload_prompt()` (JSON mode)
2. OpenAI retourne JSON structuré
3. `_clean_payload()` enlève markdown/HTML
4. Context passe JSON structuré au template
5. Affichage correct

### Mais risques persistent:

**1. Expériences hallucin**
- Prompt dit "Extract experiences from CANDIDATE DATA"
- IA peut ajouter détails: "Led team of 5" (pas dans blocks)
- Fix: Ajouter `extraction_only=true` flag ou JSON schema stricte

**2. Certifications inventées**
- Prompt accepte JSON certifications array
- IA peut ajouter: `{ "name": "AWS Certified Solutions Architect" }`
- Fix: Require certifications from `profile_blocks` uniquement

**3. Organizations hallucin**
- Company field dans expériences
- IA peut mettre "Google" si jamais dans blocks
- Fix: Validate company names vs blocks

### Données qui auraient dû être utilisées:

À la place de hallucinations, utiliser:
```python
profile_blocks = [
  { id: 1, category: "skill", title: "Python", content: "...", priority: 10 },
  { id: 2, category: "skill", title: "SQL", content: "...", priority: 9 },
  { id: 3, category: "experience", title: "Data Analyst", 
    content: "Worked on reporting", tags: ["2 years"] },
]

# IA doit limiter à:
experiences = [
  {
    title: "Data Analyst",  # ← from blocks
    company: "...",  # ← from blocks tags ou content
    bullets: ["Worked on reporting"]  # ← from blocks content, rewritten
  }
]

skills = ["Python", "SQL", "Excel"]  # ← exact matches from blocks
```

---

## 9. Flux réel des données

```
┌─────────────────────────────────────────────────────────────────┐
│ OFFRE UTILISATEUR                                               │
│                                                                 │
│ Source: URL ou texte brut                                      │
│ ↓ InputAgent.process()                                         │
│   • Détecte type (URL/text)                                   │
│   • Extrait (trafilatura si URL)                              │
│   • Retourne offer_text (ou None)                             │
│ ↓                                                               │
│ Data: offer_text (1KB-100KB)                                  │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ DB: applications TABLE                                          │
│                                                                 │
│ INSERT:                                                        │
│ • telegram_user_id                                            │
│ • raw_offer (offer_text)                                      │
│ • source_url (if URL)                                         │
│ • status = "analyzed"                                         │
│                                                                 │
│ Data persisted: application_id = 7                            │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ ANALYSIS PHASE                                                  │
│                                                                 │
│ Inputs:                                                        │
│ • offer_text                                                  │
│ • ALL profile_blocks (from DB)                                │
│                                                                 │
│ Process: AnalysisAgent.analyze()                              │
│ ↓ OpenAI (JSON mode)                                          │
│   Returns: analysis_json                                      │
│ ↓                                                               │
│ Data: analysis_json (dict)                                    │
│ {                                                              │
│   company: "Acme Corp",                                       │
│   job_title: "Senior Data Analyst",                           │
│   required_skills: ["Python", "SQL", "Tableau"],  # ❌ risky  │
│   missing_points: ["Advanced ML", "Scala"],                  │
│   profile_blocks_to_use: [1, 2, 5],                           │
│   ...                                                          │
│ }                                                              │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ MATCHING PHASE                                                  │
│                                                                 │
│ Process: MatchingAgent.enrich_analysis()                      │
│ • Validate block IDs exist (1, 2, 5 → OK)                    │
│ • Filter invalids (silently)                                  │
│                                                                 │
│ Data: analysis_json (validated block IDs)                    │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ DB: job_analyses TABLE                                          │
│                                                                 │
│ INSERT:                                                        │
│ • application_id = 7                                          │
│ • analysis_json (entire dict)                                 │
│ • missions, required_skills, etc. (duplicated)                │
│                                                                 │
│ Data persisted                                                │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ POSITIONING PHASE                                               │
│                                                                 │
│ Process: PositioningAgent.choose_angle()                      │
│ ↓ OpenAI (texte)                                              │
│   Returns: angle (validated vs VALID_ANGLES)                  │
│                                                                 │
│ Data: positioning = "Data Analyst BI"                         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ GENERATION PHASE (Utilisateur tape "CV")                       │
│                                                                 │
│ Inputs:                                                        │
│ • application_id = 7 (from user session)                     │
│ • analysis_json (from job_analyses)                          │
│ • positioning (computed above)                               │
│ • profile_blocks[to_use] (selected from DB)                 │
│ • candidate info (from config env vars)                      │
│                                                                 │
│ Process: GenerationAgent.generate_cv()                        │
│ ↓ get_cv_payload_prompt() builds prompt                       │
│ ↓ OpenAI (JSON mode)                                          │
│   Returns: cv_payload JSON                                    │
│   {                                                            │
│     title: "Marketing Data Analyst",                          │
│     summary: "...",                                           │
│     experiences: [                                            │
│       {                                                        │
│         title: "...",  # ← rewritten from blocks             │
│         company: "...",  # ← from blocks tags or made up    │
│         bullets: [...]  # ← rewritten from blocks            │
│       }                                                        │
│     ],                                                         │
│     skills_sections: [...],                                   │
│     certifications: [...]  # ❌ can hallucinate              │
│   }                                                            │
│ ↓ _clean_payload() removes markdown/HTML                      │
│ ↓ _build_candidate_info() adds candidate data                 │
│                                                                 │
│ Context = {                                                    │
│   candidate: { name: "Akim Guentas", email: "..." },         │
│   cv: cv_payload                                              │
│ }                                                              │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ TEMPLATE RENDERING                                              │
│                                                                 │
│ Process: document_service.render_cv(context)                  │
│ ↓ Jinja2 template (cv.html)                                   │
│   Returns: HTML string                                        │
│                                                                 │
│ Data: HTML (10KB-50KB)                                        │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ FILE SAVING & DB                                                │
│                                                                 │
│ Disk: outputs/app_7_cv.html                                   │
│ DB: generated_documents TABLE                                  │
│ • application_id = 7                                          │
│ • document_type = "cv"                                        │
│ • content = HTML                                              │
│ • file_path = "/outputs/app_7_cv.html"                       │
│                                                                 │
│ Data persisted                                                │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ TELEGRAM DELIVERY                                               │
│                                                                 │
│ handlers.handle_command() sends:                              │
│ • Message: "✅ CV généré"                                     │
│ • Document: app_7_cv.html (binary)                            │
│                                                                 │
│ User receives file                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Où les hallucinations s'introduisent:

1. **AnalysisAgent** — IA reçoit tous les blocks, combine librement
2. **GenerationAgent — CV Payload** — IA "rewrites" (ajoute détails)
3. **GenerationAgent — Lettre/Mail** — Texte libre (no validation)

### Où elles auraient pu être arrêtées:

- ✅ MatchingAgent — valide block IDs (fait)
- ❌ QualityAgent — vérifierait vs blocks (not called)
- ❌ Post-generation validation — n'existe pas

---

## 10. Points faibles actuels

### Critique 🔴

| Problème | Impact | Loc |
|----------|--------|-----|
| Hallucination CV | CV invente expériences/certifications | GenerationAgent, prompts |
| Lettre/Mail non validés | Documents contiennent infos fausses | handlers, generation_agent |
| Pas de post-generation audit | Rien ne vérifie le résultat | N/A |
| Profile blocks jamais constraints | IA peut combiner blocks arbitrairement | analysis_prompt |
| QualityAgent jamais appelé | Aucun guard rails | handlers |

### Important ⚠️

| Problème | Impact | Loc |
|----------|--------|-----|
| Candidate env vars vides | CV affiche nom vide | config, templates |
| Templates fragiles | Erreur Jinja = 500 | document_service |
| Logs dispersés | Debugging en prod difficile | Everywhere |
| Pas de transaction DB | Failure = partial state | application_service |
| URL extraction timeout | Bot bloque longtemps | scraping_service |
| Rate limiting absent | Potential abuse/costs | openai_service, handlers |

### Secondaire 🟡

| Problème | Impact | Loc |
|----------|--------|-----|
| PDF absent | V1 feature creep | N/A |
| Dashboard absent | No analytics | N/A |
| Soft delete not used | Data cleanup unclear | models |
| No audit trail | Who changed what | N/A |

---

## 11. Plan de correction recommandé

### Phase 1: Empêcher hallucinations (URGENT)

**Step 1a — Validation stricte post-génération (1 jour)**
```python
# app/services/quality_service.py (nouveau)

def validate_cv_content(cv_payload, profile_blocks):
    """
    Verify CV doesn't contain invented claims.
    Return (is_valid, issues).
    """
    # Check experiences companies vs blocks
    # Check certifications vs blocks
    # Check skills vs blocks
    # Etc.
```

**Step 1b — Ajouter validation dans GenerationAgent (1 jour)**
```python
# app/agents/generation_agent.py

async def generate_cv(...):
    payload = await generate_cv_payload(...)
    is_valid, issues = validate_cv_content(payload, selected_blocks)
    
    if not is_valid:
        logger.error(f"Hallucination detected: {issues}")
        # Either:
        # - Regenerate with stricter prompt
        # - Return error to user
        # - Flag for manual review
```

**Step 1c — Ajouter JSON mode à lettre/mail (2 jours)**
```python
# app/prompts/generation_prompt.py

def get_letter_payload_prompt(...):
    # Demande JSON avec structure strict
    return """
    Return JSON:
    {
      "opening": "Why interested in this role",
      "background": "Relevant background",
      "value": "Value to bring",
      "closing": "Call to action",
      "sources": {
        "opening": "block_id or none",
        "background": "block_id or none",
        ...
      }
    }
    """

# app/services/openai_service.py
async def generate_letter_payload(prompt):
    result = await call_openai(prompt, json_mode=True)
    return json.loads(result)
```

### Phase 2: Enrichir profile_blocks (3 jours)

**Ajouter colonnes:**
```python
# app/database/models.py

class ProfileBlock:
    # Existing...
    
    # NEW:
    dates = Column(String(255), nullable=True)  # "2023-2025"
    organization = Column(String(255), nullable=True)  # "Acme Corp"
    role = Column(String(255), nullable=True)  # "Senior Analyst"
    proof_level = Column(String(50), nullable=True)  # "verified", "self-reported"
    is_exportable = Column(Boolean, default=True)  # Can be used in CV?
```

**Seed avec données réelles:**
```python
blocks = [
    ProfileBlock(
        category=CategoryEnum.experience,
        title="Senior Data Analyst",
        content="Analyzed KPIs, built dashboards",
        organization="Sidel",
        dates="2023-2025",
        role="Data Analyst",
        proof_level="verified",
        tags=["Power BI", "Python", "SQL"],
        priority=10
    ),
    # ...
]
```

### Phase 3: Séparer profil / CV content (2 jours)

**Profil = Vérité:**
```python
# profile_blocks table
# - Exact, verified facts
# - No rewrites
```

**CV = Reformulation:**
```python
# cv_payload
# - Reformatted for relevance
# - But validates against profile_blocks
```

**Template = Affichage:**
```html
<!-- cv.html -->
<!-- Just renders payload -->
```

### Phase 4: Ajouter mode audit (1 jour)

**Commandes Telegram:**
```python
# app/bot/handlers.py

async def debug_profile(update, context):
    """Show all profile blocks."""
    blocks = db.query(ProfileBlock).all()
    msg = "Profile blocks:\n"
    for b in blocks:
        msg += f"• {b.title} ({b.category})\n"
    await update.message.reply_text(msg)

async def debug_last_payload(update, context):
    """Show last generated CV payload."""
    doc = db.query(GeneratedDocument).filter_by(...).first()
    if doc:
        payload = extract_payload_from_html(doc.content)
        await update.message.reply_text(f"Payload:\n{json.dumps(payload, indent=2)}")
```

**Timeline:** 7 jours total, done incrementally

---

## 12. Conclusion

### Ce qui fonctionne ✅
- ✅ Telegram interface stable
- ✅ Database schema sensible
- ✅ Agent separation clean
- ✅ OpenAI integration robuste
- ✅ Template rendering correct (après fixes)
- ✅ Error handling + debug mode added

### Ce qui ne fonctionne pas ❌
- ❌ CV generation hallucinates
- ❌ Letter/mail not validated
- ❌ No post-hoc audit
- ❌ QualityAgent ignored

### Ce qui bloque la qualité 🔴
- **Hallucination dans CV/lettre/mail** — IA invente expériences/certs/skills
- **Pas de validation stricte** — Rien ne vérifie le résultat vs profile_blocks
- **Prompts trop permissifs** — IA reçoit tous les blocks, peut combiner librement

### Prochaine action prioritaire
**Phase 1a + 1b** (steps 1a-1b du plan): Ajouter validation stricte post-génération et vérifier content vs profile_blocks. Deadline: 48h.

Sans ça, CV/documents continuent à inventer infos → Risk de candidatures rejetées ou problèmes légaux (fausses certifications).

---

## Appendix: Files not deeply audited

- `app/main.py` — FastAPI skeleton (no endpoints used)
- `app/schemas/` — Pydantic models (minimal)
- `app/database/db.py` — SQLAlchemy connection
- `app/database/seed_profile.py` — Initial data load
- `Dockerfile`, `docker-compose.yml` — Infrastructure (not code)
- Tests — No tests present (future)

---

**End of audit.** Last updated: 2026-06-14.
