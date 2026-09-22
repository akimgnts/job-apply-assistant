"""Build candidate tracking rows from read-only Gmail events.

The agent is deterministic on purpose: it proposes an operational history without
pretending that every email is a confirmed application. User confirmation still
drives durable application links and outreach status changes.
"""
import re
import unicodedata
from collections import defaultdict
from datetime import datetime


TRACKING_LABELS = (
    "cold_email",
    "application_sent",
    "application_ack",
    "recruiter_reply",
    "interview_or_test",
    "rejection",
    "job_board_alert",
    "bounce",
    "noise",
)

NOISE_SENDERS = (
    "planity.com",
    "uber.com",
    "movie-previews.com",
    "dailydoseofds.com",
)

JOB_BOARD_SENDERS = {
    "linkedin.com": "LinkedIn",
    "meteojob.com": "Meteojob",
    "apec.fr": "APEC",
    "pole-emploi.fr": "France Travail",
    "francetravail.fr": "France Travail",
    "indeed.com": "Indeed",
    "welcometothejungle.com": "Welcome to the Jungle",
}

STATUS_RANK = {
    "interview_or_test": 80,
    "recruiter_reply": 70,
    "rejection": 65,
    "bounce": 60,
    "application_ack": 45,
    "application_sent": 40,
    "cold_email": 35,
    "job_board_alert": 20,
    "noise": 0,
}


def normalize(text: str) -> str:
    text = text or ""
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def title_case(value: str) -> str:
    value = re.sub(r"\s+", " ", (value or "").strip(" -—|:·"))
    if not value:
        return ""
    fixes = {"vie": "VIE", "cdi": "CDI", "cdd": "CDD", "ia": "IA", "ai": "AI", "bi": "BI", "data": "Data"}
    return " ".join(fixes.get(part.lower(), part[:1].upper() + part[1:]) for part in value.split())


def clean_company(value: str) -> str:
    value = re.split(r"[.;\n\r]", value or "")[0]
    value = title_case(value)
    blacklist = {"Sep", "Sept", "September", "Votre Candidature", "Candidature", "Application"}
    return "" if value in blacklist else value


def sender_domain(email: str) -> str:
    return (email or "").split("@")[-1].lower()


class ApplicationTrackingAgent:
    @staticmethod
    def classify(event) -> dict:
        subject = event.subject or ""
        body = event.body_text or event.snippet or ""
        sender = event.sender_email or ""
        labels = event.labels or []
        domain = sender_domain(sender)
        text = normalize(subject + "\n" + body[:5000])

        source = "gmail"
        company = ""
        job_title = ""

        confirmed = getattr(event, "confirmed_type", None)
        aliases = {"acknowledgement": "application_ack", "interview_request": "interview_or_test", "newsletter": "job_board_alert"}
        if getattr(event, "status", None) == "processed" and confirmed:
            return {"label": aliases.get(confirmed, confirmed), "source": "gmail", "company": "", "job_title": "", "reason": "Qualification validée manuellement."}

        if "SENT" in labels:
            if not re.search(r"\bcandidature\b|\bapplication\s*[—:|-]|\bi am applying\b|\bje (?:vous )?(?:adresse|soumets|propose) ma candidature\b|\bcandidature spontanee\b|\b(?:mon|my) (?:cv|resume)\b", text):
                return {"label": "noise", "source": "noise", "company": "", "job_title": "", "reason": "Message envoyé sans preuve de candidature."}
            job_title, company = ApplicationTrackingAgent._extract_sent_target(subject, body)
            # Recipient identity is stronger evidence than employers mentioned in a CV.
            recipient_companies = {ApplicationTrackingAgent._extract_company("", "", address) for address in (getattr(event, "recipients", None) or []) if address}
            recipient_companies.discard("")
            if len(recipient_companies) == 1:
                company = next(iter(recipient_companies))
            return {
                "label": "application_sent",
                "source": "cold_email" if sender else "gmail",
                "company": company,
                "job_title": job_title,
                "reason": "Message envoyé lié à une candidature ou approche.",
            }

        if any(noise in domain for noise in NOISE_SENDERS):
            return {"label": "noise", "source": "noise", "company": "", "job_title": "", "reason": "Expéditeur non lié à la recherche d’emploi."}

        patterns = [
            ("bounce", r"undeliverable|delivery status notification|delivery has failed|adresse introuvable|mail delivery subsystem", "Notification de non-remise."),
            ("rejection", r"ne donnerons pas suite|ne donnons pas suite|pas ete retenu|pas été retenu|not been selected|not be moving forward|regret to inform|unable to offer", "Refus probable."),
            ("interview_or_test", r"entretien|interview|assessment|test technique|test de recrutement|disponibilites|disponibilités|calendly|visio", "Entretien, test ou disponibilité détecté."),
            ("recruiter_reply", r"\bhrbp\b|je les ai invites|je les ai invités|va revenir vers vous|revenons vers vous|votre profil nous interesse|votre profil nous intéresse", "Réponse recruteur ou suite humaine détectée."),
            ("application_ack", r"bien recu votre candidature|bien reçu votre candidature|candidature.*re[cç]ue|application.*received|received your application|thank you for applying|candidature.*enregistr", "Accusé de réception de candidature."),
        ]
        for label, pattern, reason in patterns:
            if re.search(pattern, text, re.S):
                return {
                    "label": label,
                    "source": source,
                    "company": ApplicationTrackingAgent._extract_company(subject, body, sender),
                    "job_title": ApplicationTrackingAgent._extract_job_title(subject),
                    "reason": reason,
                }

        for board_domain, board_name in JOB_BOARD_SENDERS.items():
            if board_domain in domain or board_domain in normalize(subject):
                return {
                    "label": "job_board_alert",
                    "source": "job_board",
                    "company": board_name,
                    "job_title": ApplicationTrackingAgent._extract_job_title(subject) or "Alerte emploi",
                    "reason": f"Alerte ou notification emploi détectée depuis {board_name}.",
                }

        if ApplicationTrackingAgent._looks_like_job_search(text, subject, sender):
            return {
                "label": "recruiter_reply" if subject.lower().startswith("re:") else "unknown",
                "source": source,
                "company": ApplicationTrackingAgent._extract_company(subject, body, sender),
                "job_title": ApplicationTrackingAgent._extract_job_title(subject),
                "reason": "Message lié à une candidature ou à un échange recruteur.",
            }

        return {"label": "noise", "source": "noise", "company": "", "job_title": "", "reason": "Aucun signal fiable de recherche d’emploi."}

    @staticmethod
    def build_opportunities(events) -> list[dict]:
        grouped = defaultdict(list)
        events = [event for event in events if event.status != "archived"]
        infos = {event.id: ApplicationTrackingAgent.classify(event) for event in events}
        qualified_threads = {event.thread_id for event in events if event.thread_id and infos[event.id]["label"] not in ("noise", "job_board_alert")}
        thread_apps = defaultdict(set)
        for event in events:
            if event.thread_id and event.application_id:
                thread_apps[event.thread_id].add(event.application_id)
        for event in events:
            info = infos[event.id]
            if info["label"] == "noise" and event.thread_id in qualified_threads:
                info = {"label": "application_sent" if "SENT" in (event.labels or []) else "recruiter_reply", "source": "gmail", "company": "", "job_title": "", "reason": "Échange dans un fil de candidature identifié."}
            linked_apps = thread_apps.get(event.thread_id, set())
            if info["label"] == "noise":
                key = f"noise:{event.id}"
            elif event.application_id:
                key = f"app:{event.application_id}"
            elif len(linked_apps) == 1:
                key = f"app:{next(iter(linked_apps))}"
            elif event.thread_id and info["label"] != "job_board_alert":
                key = f"thread:{event.thread_id}"
            else:
                company = normalize(info.get("company") or ApplicationTrackingAgent._extract_company(event.subject or "", event.body_text or "", event.sender_email or ""))
                title = normalize(info.get("job_title") or ApplicationTrackingAgent._extract_job_title(event.subject or ""))
                key = f"signal:{company}:{title}:{event.thread_id or event.id}"
            grouped[key].append((event, info))

        rows = []
        for key, items in grouped.items():
            useful = [item for item in items if item[1]["label"] != "noise"]
            if not useful:
                continue
            milestones = [item for item in useful if item[1]["label"] in ("rejection", "interview_or_test", "bounce")]
            best_event, best_info = max(milestones or useful, key=lambda item: item[0].received_at or datetime.min)
            latest_event, latest_info = max(useful, key=lambda item: item[0].received_at or datetime.min)
            target_items = sorted(useful, key=lambda item: ("SENT" not in (item[0].labels or []), item[0].received_at or datetime.min))
            target_company = next((info["company"] for _, info in target_items if info.get("company")), "")
            target_title = next((info["job_title"] for _, info in target_items if info.get("job_title")), "")
            labels = sorted({info["label"] for _, info in useful}, key=lambda label: -STATUS_RANK.get(label, 0))
            rows.append({
                "id": key,
                "company": target_company or "Entreprise à préciser",
                "job_title": target_title or "Poste à préciser",
                "identity_needs_review": not target_company or not target_title or best_info["label"] == "unknown",
                "sent_count": sum("SENT" in (event.labels or []) for event, _ in useful),
                "received_count": sum("SENT" not in (event.labels or []) for event, _ in useful),
                "source": best_info.get("source") or latest_info.get("source") or "gmail",
                "status": ApplicationTrackingAgent._status_from_label(best_info["label"]),
                "latest_label": latest_info["label"],
                "labels": labels,
                "email_count": len(useful),
                "needs_review_count": sum(1 for event, _ in useful if event.status == "pending"),
                "processed_count": sum(1 for event, _ in useful if event.status == "processed"),
                "archived_count": sum(1 for event, _ in useful if event.status == "archived"),
                "application_id": int(key.split(":", 1)[1]) if key.startswith("app:") else None,
                "latest_event_id": latest_event.id,
                "latest_subject": latest_event.subject,
                "latest_sender": latest_event.sender_email,
                "latest_received_at": latest_event.received_at,
                "event_ids": [event.id for event, _ in sorted(useful, key=lambda item: item[0].received_at or datetime.min, reverse=True)],
            })
        return sorted(rows, key=lambda row: (row["latest_received_at"] or datetime.min), reverse=True)

    @staticmethod
    def _status_from_label(label: str) -> str:
        return {
            "interview_or_test": "interview",
            "recruiter_reply": "reply",
            "rejection": "rejected",
            "bounce": "bounced",
            "application_ack": "acknowledged",
            "application_sent": "sent",
            "cold_email": "sent",
            "job_board_alert": "job_board",
        }.get(label, "needs_review")

    @staticmethod
    def _looks_like_job_search(text: str, subject: str, sender: str) -> bool:
        if re.search(r"\bcandidature\b|\brecrutement\b|\brecruit(?:ing|er|ment)\b|\bjob application\b|\bentretien (?:de recrutement|pour le poste)\b|\bhrbp\b", text):
            return True
        domain = sender_domain(sender)
        return bool(re.search(r"talent|recruit|jobs?|career|rh|hr", domain))

    @staticmethod
    def _extract_sent_target(subject: str, body: str) -> tuple[str, str]:
        title = ApplicationTrackingAgent._extract_job_title(subject)
        # Only an explicit subject target is used; body text contains former employers.
        company = ApplicationTrackingAgent._extract_company(subject, "", "")
        return title, company

    @staticmethod
    def _extract_job_title(text: str) -> str:
        text = re.sub(r"^(?:(?:re|fwd|tr):\s*)+", "", text or "", flags=re.I)
        # Remove candidate signatures and application boilerplate before extracting a role.
        text = text.split("|")[0]
        text = re.sub(r"^(?:application|candidature)\s*(?:V\.?I\.?E\.?)?\s*[—–:-]\s*", "", text, flags=re.I)
        text = re.split(r"\s[—–]\s(?:application|candidature)", text, flags=re.I)[0]
        pattern = r"\b((?:(?:VIE|CDI|CDD)\s+)?(?:(?:Data|Business|BI|Product|Ops|AI|IA|Operations)\s+(?:Performance\s+)?(?:Analyst|Scientist|Engineer|Manager|Analyste|Consultant|Developer|Associate)|(?:Ingénieur|Ingenieur|Analyste|Consultant|Développeur)\s+(?:Data|BI|Python)|PMO)(?:\s*(?:/|&)\s*(?:Data Scientist|Data Analyst|Développeur Python|BI))*)\b"
        match = re.search(pattern, text, re.I)
        return title_case(match.group(1)) if match else ""

    @staticmethod
    def _extract_company(subject: str, body: str, sender: str) -> str:
        combined = subject
        for pattern in (
            r"\|\s*([A-Z][A-Za-z0-9& .'-]{2,60})",
            r"\bchez\s+([A-Z][A-Za-z0-9& .'-]{2,60})",
            r"\bwithin\s+([A-Z][A-Za-z0-9& .'-]{2,60})",
        ):
            match = re.search(pattern, combined)
            if match:
                company = clean_company(match.group(1))
                if company and not re.search(r"akim|guentas|brussels|paris|belgium|france", company, re.I):
                    return company
        domain = sender_domain(sender)
        excluded = ("gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "linkedin.com", "meteojob.com", "indeed.com", "free-work.com", "hireflix.com", "workday.com", "myworkday.com", "talent-soft.com", "successfactors.com")
        if domain and "@" in sender and not any(domain == part or domain.endswith("." + part) for part in excluded):
            parts = domain.split(".")
            root = parts[-2] if len(parts) > 1 else ""
            if root not in ("noreply", "no-reply", "mail", "email", "jobs", "jobalerts"):
                return clean_company(root)
        return ""
