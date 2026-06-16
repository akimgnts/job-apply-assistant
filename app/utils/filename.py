"""Utility for generating safe filenames for documents.

Converts document metadata to clean, filesystem-safe filenames.
"""

import unicodedata
import re


def safe_document_filename(
    candidate_name: str,
    job_title: str,
    company: str,
    document_type: str,
    extension: str = "pdf"
) -> str:
    """Generate safe filename for document.

    Args:
        candidate_name: Full name of candidate
        job_title: Job position title
        company: Company name
        document_type: One of "CV", "Lettre", "Mail"
        extension: File extension (pdf, html, txt)

    Returns:
        Safe filename string

    Examples:
        CV_Akim_Guentas_Chef_de_Projet_Marketing_John_Paul.pdf
        Lettre_Akim_Guentas_Data_Analyst_Converteo.pdf
        Mail_Akim_Guentas_Senior_Engineer_Google.txt
    """

    def normalize(text: str) -> str:
        """Remove accents and normalize text."""
        if not text:
            return ""
        # Decompose accented chars
        nfd = unicodedata.normalize("NFD", text)
        # Keep only ASCII
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    def clean(text: str) -> str:
        """Clean and format text for filename."""
        if not text:
            return ""
        # Normalize accents
        text = normalize(text)
        # Remove special chars, keep only alphanumeric + spaces
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
        # Replace spaces with underscores
        text = re.sub(r"\s+", "_", text)
        # Remove consecutive underscores
        text = re.sub(r"_+", "_", text)
        # Remove leading/trailing underscores
        text = text.strip("_")
        return text

    # Clean each component
    clean_name = clean(candidate_name)
    clean_title = clean(job_title)
    clean_company = clean(company)

    # Build filename: {type}_{name}_{title}_{company}.{ext}
    filename = f"{document_type}_{clean_name}_{clean_title}_{clean_company}.{extension}"

    # Limit length (filesystem max is often 255, be safe with 120)
    if len(filename) > 120:
        # Truncate parts if needed
        max_part = 30
        clean_name = clean_name[:max_part]
        clean_title = clean_title[:max_part]
        clean_company = clean_company[:max_part]
        filename = f"{document_type}_{clean_name}_{clean_title}_{clean_company}.{extension}"

    return filename


def document_extension(document_type: str) -> str:
    """Get file extension for document type.

    Args:
        document_type: "cv", "letter", or "mail"

    Returns:
        Extension: "pdf", "pdf", or "txt"
    """
    extensions = {
        "cv": "pdf",
        "letter": "pdf",
        "mail": "txt",
    }
    return extensions.get(document_type.lower(), "pdf")
