# Roadmap

## V1 (MVP) — Current

**Status**: Complete

### Features
- ✅ Telegram bot interface
- ✅ URL + text input handling
- ✅ Trafilatura-based extraction (with fallback)
- ✅ OpenAI offer analysis
- ✅ Profile matching
- ✅ Positioning angle selection
- ✅ CV/letter/mail generation
- ✅ Document storage in DB
- ✅ Validation commands (GO/CV/LETTRE/MAIL)
- ✅ Quality checks (no invented claims)
- ✅ PostgreSQL backend
- ✅ Alembic migrations
- ✅ Docker setup

### Profile Seed
- ✅ Sidel experience
- ✅ Elevia project
- ✅ Made By Curve freelance
- ✅ Education
- ✅ Data skills
- ✅ IA skills

### Limitations
- No PDF (users print to PDF)
- No OCR
- Single user per bot instance
- No web interface
- Simple scoring algorithm

---

## V1.1 (Quality Improvements) — Next ~2 weeks

### Goals
Stabilize MVP, improve document quality, better error handling.

### Features

#### Better URL Handling
- [ ] Fallback to Readability parser if trafilatura fails
- [ ] Support LinkedIn job pages (specific parsing)
- [ ] Timeout on very large pages (30s limit)
- [ ] Better extraction detection (min content threshold configurable)

#### Enhanced Generation
- [ ] Multiple CV formats (focused/comprehensive)
- [ ] Letter structure variations (creative/formal)
- [ ] Mail template variants (first-contact/follow-up)
- [ ] ATS keyword optimization in CV

#### User Experience
- [ ] `/profile` command to view current profile
- [ ] `/reload_profile` to refresh from DB
- [ ] Better error messages (more actionable)
- [ ] Typing indicators for long operations
- [ ] Session persistence (edit/retry analysis)

#### Quality Improvements
- [ ] Enhanced quality checks (fluency detection)
- [ ] Confidence scores on generations
- [ ] Manual override for rejected documents
- [ ] A/B testing variants

#### Monitoring
- [ ] Usage tracking (applications/day)
- [ ] Error rate monitoring
- [ ] OpenAI cost tracking
- [ ] Performance metrics (latency per step)

---

## V2 (Polish & Scale) — ~4-6 weeks

### Goals
Production-ready, multi-user support, advanced features.

### Features

#### Multi-User
- [ ] User authentication (simple token-based)
- [ ] Per-user profile customization
- [ ] Shared profile blocks + user overrides
- [ ] User analytics dashboard
- [ ] Rate limiting per user

#### Advanced Matching
- [ ] Custom weight scoring
- [ ] Skill level mapping (junior/mid/senior)
- [ ] Company matching (industry, stage, size)
- [ ] Salary expectations matching
- [ ] Remote/location matching

#### Profile Management
- [ ] `/edit_profile` command
- [ ] Add custom profile blocks
- [ ] Priority adjustment
- [ ] Truth level management
- [ ] Block versioning

#### Enhanced Documents
- [ ] Multiple CV sections (technical, soft skills)
- [ ] Cover letter with company research
- [ ] Email with personalization tokens
- [ ] Document version history
- [ ] Export as plain text + formatted

#### Integration
- [ ] LinkedIn job scraping (with auth)
- [ ] Job board integrations (Indeed, AngelList)
- [ ] Email sending from app
- [ ] Calendar integration (interview scheduling)

---

## V3 (Premium) — ~8-10 weeks

### Goals
PDF generation, web dashboard, advanced AI features.

### Features

#### PDF Generation
- [ ] Playwright + wkhtmltopdf for CV PDF
- [ ] Letter PDF with proper formatting
- [ ] Multi-page CV support
- [ ] PDF signature injection
- [ ] Custom fonts/branding

#### Web Dashboard
- [ ] Application history view
- [ ] Document builder UI
- [ ] Profile management interface
- [ ] Analytics dashboard
- [ ] Export/archive functionality

#### Advanced AI
- [ ] Custom positioning angle creation
- [ ] Behavioral question preparation
- [ ] Salary negotiation advisor
- [ ] Company research agent
- [ ] Interview prep suggestions

#### Collaboration
- [ ] Share applications with mentors
- [ ] Feedback collection
- [ ] Collaborative CV editing
- [ ] Comments/annotations

---

## V4 (Enterprise) — ~3-4 months

### Goals
Integration, advanced analytics, team features.

### Features

#### Elevia Integration
- [ ] Two-way sync with Elevia matching engine
- [ ] Unified profile canonicalization
- [ ] Shared skill taxonomy
- [ ] Score alignment
- [ ] Bi-directional updates

#### Advanced Analytics
- [ ] Success rate by positioning
- [ ] Industry/role performance
- [ ] Geographic matching data
- [ ] Skill demand analysis
- [ ] Career path recommendations

#### Team Features
- [ ] Recruiter dashboard
- [ ] Bulk candidate processing
- [ ] Hiring workflow automation
- [ ] Interview scheduling
- [ ] Feedback loops

#### API
- [ ] REST API for integrations
- [ ] Webhook support
- [ ] OAuth2 authentication
- [ ] GraphQL interface (optional)

---

## V5+ (Future)

### Speculative Features
- Fine-tuned models on successful applications
- Cached embeddings for fast matching
- Multi-language support
- Video interview preparation
- Salary range prediction
- Job market trend analysis
- Machine learning-based positioning

---

## Timeline

| Phase | Target | Effort | Dependencies |
|-------|--------|--------|--------------|
| V1 | ✅ Done | 1 week | OpenAI, Telegram |
| V1.1 | 2w | 1-2 weeks | User feedback |
| V2 | 6w | 3-4 weeks | DB scaling |
| V3 | 10w | 3-4 weeks | Playwright, PDF libs |
| V4 | 4m | 4-6 weeks | Elevia API |
| V5+ | TBD | TBD | Market demand |

---

## Known Limitations & Workarounds

### V1 Limitations

| Issue | Impact | Workaround |
|-------|--------|-----------|
| No PDF | Users can't auto-email | Browser Print → PDF |
| No OCR | Image-only offers fail | Paste text manually |
| Single user | Bot blocked by privacy | Create separate bot per user |
| Simple scoring | Misses nuances | Manual override |
| English/French only | Limited market | Add translations |

### V2 Will Address
- Multi-user via tokens
- Better error recovery
- Configurable scoring
- i18n support

---

## Investment Priorities

### High ROI
1. **Multi-user** (V2) — opens up to market
2. **PDF generation** (V3) — email integration
3. **Elevia sync** (V4) — leverages existing platform

### Nice-to-have
1. Advanced analytics
2. Collaboration features
3. Advanced AI agents

### Maybe
1. Mobile app (use Telegram instead)
2. Desktop client (use web)

---

## Success Metrics

### V1
- Bot responds to offers ✅
- Generates documents ✅
- No invented content ✅
- Saves to DB ✅

### V1.1
- Error rate < 5%
- OpenAI cost < $0.10/application
- User session > 2 applications

### V2
- 50+ active users
- 3+ applications/user/week
- NPS > 7

### V3
- 500+ active users
- PDF exports > 80% of applications
- Dashboard adoption > 60%

### V4
- 2000+ users
- Elevia integration active
- Enterprise customers
- $X revenue/month

---

## Architecture Debt

### Current
- No request validation on bot inputs
- Logging is basic (no levels)
- No caching
- No rate limiting

### V1.1 Should Add
- Input validation with error messaging
- Structured logging (JSON)
- Redis for session caching
- Per-user rate limits

### V2 Should Refactor
- Extract bot logic into service layer (current handlers are thin, good)
- Add middleware for auth
- Response pagination for large histories

---

## Testing Strategy

### V1 (Current)
- Manual testing via Telegram

### V1.1
- Unit tests for agents
- Integration tests for services
- Prompt testing (consistency)

### V2
- API endpoint tests
- Multi-user scenario tests
- Load testing (10 concurrent users)

### V3+
- End-to-end browser tests (dashboard)
- Performance benchmarks
- Stress testing

---

## Dependencies

### Required (Always)
- OpenAI API access
- PostgreSQL
- Telegram

### Optional
- Redis (V1.1, caching)
- Playwright (V3, PDF)
- Sentry (monitoring)
- DataDog (metrics)

### Future
- Elevia API (V4)
- Auth provider (OAuth2, V2)
