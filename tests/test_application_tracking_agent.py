from datetime import datetime

from app.database.models import EmailEvent
from app.services.application_tracking_agent import ApplicationTrackingAgent


def event(identifier, subject, body="", sender="akim@example.org", labels=None, thread=None):
    return EmailEvent(
        id=identifier,
        owner_id="owner",
        mailbox="akim@example.org",
        gmail_message_id=f"m{identifier}",
        thread_id=thread or f"t{identifier}",
        sender_email=sender,
        sender_name=sender.split("@")[0],
        subject=subject,
        snippet=body[:120],
        body_text=body,
        labels=labels or [],
        detected_type="unknown",
        status="pending",
        received_at=datetime(2026, 9, 18, 10, identifier),
    )


def test_classifies_job_search_email_types():
    assert ApplicationTrackingAgent.classify(event(1, "Application — VIE Data Analyst | TotalEnergies", labels=["SENT"]))["label"] == "application_sent"
    assert ApplicationTrackingAgent.classify(event(2, "Votre candidature a bien été reçue", "Nous avons bien reçu votre candidature"))["label"] == "application_ack"
    assert ApplicationTrackingAgent.classify(event(3, "Re: candidature", "Seriez-vous disponible pour un entretien la semaine prochaine ?"))["label"] == "interview_or_test"
    assert ApplicationTrackingAgent.classify(event(4, "Suite à votre candidature", "Nous ne donnerons pas suite à votre candidature"))["label"] == "rejection"
    assert ApplicationTrackingAgent.classify(event(5, "Delivery Status Notification", "Delivery has failed"))["label"] == "bounce"
    assert ApplicationTrackingAgent.classify(event(6, "Votre alerte emploi LinkedIn", "De nouvelles offres correspondent à vos préférences", sender="jobalerts-noreply@linkedin.com"))["label"] == "job_board_alert"
    assert ApplicationTrackingAgent.classify(event(7, "Confirmation de rendez-vous Barberia", "Réservation confirmée chez le barbier", sender="noreply@planity.com"))["label"] == "noise"


def test_extracts_company_job_source_for_candidate_email():
    item = event(
        1,
        "Application — VIE Data Scientist & Data Analyst | TotalEnergies",
        "Dear Ms Bacaud, I am applying for the VIE Data Scientist & Data Analyst position within TotalEnergies Charging Solutions Belgium.",
        labels=["SENT"],
    )

    result = ApplicationTrackingAgent.classify(item)

    assert result["company"] == "TotalEnergies"
    assert result["job_title"] == "VIE Data Scientist & Data Analyst"
    assert result["source"] == "cold_email"


def test_groups_thread_into_single_opportunity_with_latest_status():
    sent = event(1, "Application — Data Analyst | Niji", "Bonjour Niji", labels=["SENT"], thread="niji-thread")
    reply = event(2, "Re: Application — Data Analyst | Niji", "Votre candidature a bien été enregistrée ; notre HRBP va revenir vers vous.", sender="recruteur@niji.fr", thread="niji-thread")
    reply.received_at = datetime(2026, 9, 19, 9)

    rows = ApplicationTrackingAgent.build_opportunities([sent, reply])

    assert len(rows) == 1
    row = rows[0]
    assert row["company"] == "Niji"
    assert row["job_title"] == "Data Analyst"
    assert row["email_count"] == 2
    assert row["status"] == "reply"
    assert row["latest_label"] == "recruiter_reply"
    assert row["needs_review_count"] == 2


def test_keeps_job_board_alerts_as_useful_market_rows():
    alert = event(1, "Meteojob — Data Analyst CDI Paris", "Une offre Data Analyst chez Acme est disponible", sender="alerte@meteojob.com")

    rows = ApplicationTrackingAgent.build_opportunities([alert])

    assert rows[0]["source"] == "job_board"
    assert rows[0]["status"] == "job_board"
    assert rows[0]["company"] == "Meteojob"


def test_recruiter_interview_beats_job_board_mentions_in_body():
    item = event(
        1,
        "Your virtual interview at Criteo is in one hour!",
        "You may have seen the role on linkedin.com, but this is your interview reminder.",
        sender="recruiting@criteo.com",
    )

    result = ApplicationTrackingAgent.classify(item)

    assert result["label"] == "interview_or_test"
    assert result["company"] == "Criteo"
