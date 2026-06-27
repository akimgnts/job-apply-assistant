# 🏗️ Unified Pipeline Plan - Refactoring for Unified UX

**Objectif:** Un seul système pour toutes les sources (URL, DB, texte, historique)  
**Vision:** L'utilisateur ne voit qu'un seul flow quelque soit la source

---

## 📊 État Technique Actuel

### ✅ Ce qui existe déjà

| Question | Status | Détail |
|----------|--------|--------|
| Q1: Application_id pour URL? | ✅ | `create_application()` dans `handle_offer()` |
| Q2: Offres DB → application? | ✅ | `elevia_load_offer()` appelle `create_application()` |
| Q3: Pipeline commune? | ✅ | `analyze()` + `generate_*()` accepte offer_text |
| Q6: Documents liés app_id? | ✅ | `GeneratedDocument.application_id` ForeignKey |
| Q7: Régénération? | ✅ | `regenerate_callback()` existe |

### ⚠️ Ce qui manque ou est fragmenté

| Question | Status | Problème |
|----------|--------|----------|
| Q4: Contexte utilisateur? | ⚠️ | `context.user_data` (15 utilisations) vs `UserSession` DB |
| Q5: Agent IA context-aware? | ⚠️ | Reçoit `db + user_id`, peut trouver app mais pas structuré |
| Q8: Callbacks centralisés? | ⚠️ | Dispersés dans 3 fichiers (handlers, intelligence, career) |
| Q9: normalize_offer() commun? | ⚠️ | Code existe mais pas centralisé |
| Q10: Schéma unifié offres? | ⚠️ | URL et DB offres retournent format différent? |

---

## 🎯 Plan de Refactoring (5 Phases)

### Phase 0: Préparation (2h)

#### 0.1 Créer ApplicationContext unifié

**Fichier:** `app/context/application_context.py`

```python
class ApplicationContext:
    """Contexte partagé pour toute candidature"""
    
    def __init__(self, application_id: int):
        self.application_id = application_id
        self.source_type: str  # 'url' | 'database' | 'text' | 'history'
        self.source_offer_id: Optional[str]  # Pour BD offres
        
        # État courant
        self.analysis: Optional[dict]
        self.positioning: str
        self.documents_generated: dict  # {cv, letter, mail}
        
    @staticmethod
    def from_application(app: Application) -> 'ApplicationContext':
        """Charger depuis DB"""
        pass
    
    def save(self, db: Session) -> None:
        """Persister le contexte"""
        pass
    
    def get_documents(self, db: Session) -> dict:
        """Récupérer les documents générés"""
        pass
```

#### 0.2 Centraliser normalize_offer()

**Fichier:** `app/services/offer_normalization_service.py`

```python
class OfferNormalizationService:
    """Unifie offres URL et DB"""
    
    @staticmethod
    def normalize_from_text(text: str) -> Dict[str, Any]:
        """Offre copiée/collée"""
        return {
            "job_title": "...",
            "company": "...",
            "raw_text": text,
            "source_type": "text",
        }
    
    @staticmethod
    def normalize_from_url(url: str) -> Dict[str, Any]:
        """Offre depuis URL"""
        return {
            "job_title": "...",
            "raw_text": "...",
            "source_type": "url",
            "source_url": url,
        }
    
    @staticmethod
    def normalize_from_database(offer_db: Dict) -> Dict[str, Any]:
        """Offre depuis Elevia ou autre DB"""
        return {
            "job_title": offer_db.get("title"),
            "company": offer_db.get("company"),
            "raw_text": offer_db.get("description"),
            "source_type": "database",
            "source_offer_id": offer_db.get("id"),
            "source_database": "elevia",
        }
    
    @staticmethod
    def normalize_from_application(app: Application) -> Dict[str, Any]:
        """Offre depuis historique"""
        return {
            "job_title": app.job_title,
            "company": app.company,
            "raw_text": app.raw_offer,
            "source_type": "history",
            "source_application_id": app.id,
        }
```

---

### Phase 1: Unifier Pipeline (3h)

#### 1.1 Créer ProcessOfferService

**Fichier:** `app/services/process_offer_service.py`

```python
class ProcessOfferService:
    """Pipeline unique pour toute offre"""
    
    @staticmethod
    async def process_offer(
        db: Session,
        user_id: str,
        offer_data: Dict,  # Résultat de normalize_offer()
    ) -> ApplicationContext:
        """
        1. Créer application_id
        2. Analyser offre
        3. Enrichir analyse
        4. Retourner contexte
        """
        
        # Créer application
        app = create_application(
            db,
            telegram_user_id=user_id,
            raw_offer=offer_data["raw_text"],
            source_url=offer_data.get("source_url"),
        )
        
        # Analyser
        analysis = await AnalysisAgent.analyze(db, offer_data["raw_text"])
        analysis = MatchingAgent.enrich_analysis(analysis, db)
        
        # Enrichir par contexte source (DB vs URL)
        if offer_data["source_type"] == "database":
            analysis = OfferEnrichmentService.enrich_analysis_with_elevia_context(
                analysis,
                offer_data["elevia_context"],
            )
        
        # Sauvegarder
        save_analysis(db, app.id, analysis)
        update_application_with_analysis(db, app.id, analysis)
        
        # Retourner contexte
        context = ApplicationContext.from_application(app)
        context.analysis = analysis
        return context
```

#### 1.2 Refactoriser handlers pour utiliser ProcessOfferService

**Avant (dispersé):**
```python
# handlers.py
async def handle_offer():
    analysis = await AnalysisAgent.analyze(...)
    analysis = MatchingAgent.enrich_analysis(...)
    
# elevia_handlers.py
async def elevia_load_offer():
    analysis = await AnalysisAgent.analyze(...)
    analysis = MatchingAgent.enrich_analysis(...)
    analysis = OfferEnrichmentService.enrich_analysis_with_elevia_context(...)
```

**Après (unifié):**
```python
# handlers.py
async def handle_offer():
    offer_data = OfferNormalizationService.normalize_from_url(raw_input)
    context = await ProcessOfferService.process_offer(db, user_id, offer_data)
    show_result(context)

# elevia_handlers.py
async def elevia_load_offer():
    offer_data = OfferNormalizationService.normalize_from_database(elevia_offer)
    context = await ProcessOfferService.process_offer(db, user_id, offer_data)
    show_result(context)  # MÊME FONCTION
```

---

### Phase 2: Context-Aware IA (2h)

#### 2.1 Améliorer IntelligenceAgent

**Fichier:** `app/agents/intelligence_agent.py`

```python
class IntelligenceAgent:
    
    @staticmethod
    async def analyze_user_question(
        db: Session,
        user_id: str,
        question: str,
        context: Optional[ApplicationContext] = None,  # NOUVEAU
    ) -> str:
        """Analyser question avec contexte optionnel"""
        
        if context:
            # Mode candidature - question sur offre active
            return await IntelligenceAgent._analyze_with_offer_context(
                db, user_id, question, context
            )
        else:
            # Mode global - question sans offre
            return await IntelligenceAgent._analyze_global(
                db, user_id, question
            )
    
    @staticmethod
    async def _analyze_with_offer_context(
        db: Session,
        user_id: str,
        question: str,
        context: ApplicationContext,
    ) -> str:
        """Répondre en contexte d'une offre active"""
        prompt = f"""
        Utilisateur: {question}
        
        Contexte: Candidature en cours
        - Offre: {context.analysis['job_title']} @ {context.analysis['company']}
        - Score: {context.analysis['match_score']}/10
        - Angle: {context.positioning}
        
        Réponds spécifiquement par rapport à cette offre.
        """
        return await generate_response(prompt)
```

#### 2.2 Stocker ApplicationContext dans context.user_data

```python
# Dans telegram_bot.py handlers
async def show_result(update, context, app_context: ApplicationContext):
    # Sauvegarder contexte
    context.user_data["current_application_context"] = {
        "application_id": app_context.application_id,
        "source_type": app_context.source_type,
        "analysis": app_context.analysis,
        "positioning": app_context.positioning,
    }
    
    # Montrer résultat avec boutons unifiés
    await query.edit_message_text(
        text=format_result(app_context),
        reply_markup=unified_result_menu(app_context)
    )

def unified_result_menu(context: ApplicationContext):
    """Menu unique pour tout résultat"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Générer candidature", callback_data="gen_all")],
        [InlineKeyboardButton("🤖 Question IA", callback_data="ask_ia")],
        [InlineKeyboardButton("💾 Sauvegarder", callback_data="save_app")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ])
```

---

### Phase 3: Unifier Menu Principal (1.5h)

**Fichier:** `app/bot/keyboards.py`

```python
def main_menu() -> InlineKeyboardMarkup:
    """Menu principal unifié"""
    keyboard = [
        [InlineKeyboardButton("➕ Nouvelle candidature", callback_data="new_application")],
        [InlineKeyboardButton("🔎 Explorer les offres", callback_data="explore_offers")],
        [InlineKeyboardButton("🤖 Agent IA", callback_data="intelligence_menu")],
        [InlineKeyboardButton("📂 Candidatures", callback_data="my_applications")],
        [InlineKeyboardButton("⚙️ Plus", callback_data="more_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def more_menu() -> InlineKeyboardMarkup:
    """Sous-menu"""
    keyboard = [
        [InlineKeyboardButton("👤 Profil", callback_data="view_profile")],
        [InlineKeyboardButton("📄 Mon CV", callback_data="view_master_cv")],
        [InlineKeyboardButton("⚙️ Paramètres", callback_data="settings")],
        [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)
```

**Nouvelle flow:**
```
/start → main_menu()
  ├─ ➕ → Choix source (URL/Offre/Texte)
  ├─ 🔎 → Filters + List + Selection → Pipeline unifié
  ├─ 🤖 → Intelligence (context-aware)
  ├─ 📂 → History → Selection → Context loaded
  └─ ⚙️ → more_menu()
```

---

### Phase 4: Fixer Navigation Incomplète (2h)

**Appliquer à tous les handlers:**

```python
# Pattern: Chaque réponse doit avoir une action

# ❌ AVANT
async def help_command():
    await update.message.reply_text(help_text)

# ✅ APRÈS
async def help_command():
    await update.message.reply_text(
        help_text,
        reply_markup=back_home(),
    )

# ❌ AVANT
except Exception as e:
    await update.message.reply_text(f"❌ Erreur: {e}")

# ✅ APRÈS
except Exception as e:
    logger.error(..., exc_info=True)
    await update.message.reply_text(
        f"❌ Erreur\n\n{str(e)[:100]}",
        reply_markup=back_home(),
    )
```

**Checklist:**
- [ ] `/help` → `back_home()`
- [ ] `/last` → boutons action
- [ ] `/my_profile` → boutons action
- [ ] Tous les `except` → `back_home()`
- [ ] Elevia commands → boutons ou retour
- [ ] Messages vides → `back_home()`

---

### Phase 5: Tests & Validation (2h)

#### 5.1 Test Flows

```python
# Flow 1: URL → génération
/start → ➕ Nouvelle → Coller URL → Analysé → Générer → Sauvegardé

# Flow 2: DB → génération
/start → 🔎 Explorer → Filtrer → Sélectionner → Analysé (même écran!) → Générer

# Flow 3: Historique → Rédiffuser
/start → 📂 Candidatures → Sélectionner → Régénérer

# Flow 4: IA contextuelle
/start → ➕ → Analyser → 🤖 Question → (reçoit contexte) → Répondre → Générer
```

#### 5.2 Vérifier Unification

- [ ] Même `analyze()` pour URL et DB ✅
- [ ] Même `generate()` pour URL et DB ✅
- [ ] Même menu résultat (+ IA) ✅
- [ ] Même `ApplicationContext` ✅
- [ ] IA reçoit offre active ✅
- [ ] Aucun écran mort (sans bouton) ✅

---

## 📈 Implémentation Par Sprint

### Sprint 1 (4h): Fondations
- [ ] `ApplicationContext` classe
- [ ] `OfferNormalizationService`
- [ ] Tests unitaires

### Sprint 2 (5h): Pipeline
- [ ] `ProcessOfferService`
- [ ] Refactoriser `handle_offer()`
- [ ] Refactoriser `elevia_load_offer()`
- [ ] Tests integration

### Sprint 3 (3h): IA & Menu
- [ ] Agent context-aware
- [ ] `main_menu()` unifié
- [ ] Tests E2E

### Sprint 4 (2h): Navigation
- [ ] Fixer tous les handlers
- [ ] Ajouter boutons manquants
- [ ] Tests UX

### Sprint 5 (1h): Validation
- [ ] Tests de tous les flows
- [ ] Performance
- [ ] Documentation

**Total: ~15 heures de refactoring**

---

## 🚀 Résultat Final

**Utilisateur voit:**
```
Un seul système
Peu importe la source

URL → Analysé → Générer
DB → Analysé → Générer (MÊME écran)
Historique → Régénérer

Contexte partagé = IA plus intelligente
Pas de boutons cassés = Navigation fluide
```

**Backend voit:**
```
ApplicationContext unique
Pipeline partagée
Callbacks centralisés
IA context-aware
Pas de duplication
```

---

## ⚠️ Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking existing users | Feature-flag pour activer nouveau menu |
| Database changes | Migration Alembic pour ApplicationContext table |
| IA responses change | A/B test prompts avant deploy |
| Callbacks conflict | Namespace patterns (`app_new_*` vs `app_old_*`) |

---

## Questions Ouvertes

1. **Veux-tu garder `/analyze_offer` command ou seulement boutons?**
   - Recommendation: Buttons only - plus fluide

2. **Veux-tu historique intelligent (offres similaires)?**
   - Recommendation: Oui, via `Agent IA` mode recherche

3. **Veux-tu A/B test menu avant full deploy?**
   - Recommendation: Oui, via `context.user_data["new_ui"]`

---

## Résumé

🎯 **But:** Un seul système pour URL, DB, texte, historique  
🏗️ **Architecture:** ApplicationContext + ProcessOfferService  
🤖 **IA:** Context-aware  
💻 **UX:** Menu unifié, navigation fluide  
⏱️ **Timeline:** ~15h de refactoring  
✅ **Résultat:** Utilisateur voit un seul produit

