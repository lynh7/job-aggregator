import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader


PARSER_VERSION = "candidate-parser-v1"
KNOWN_SKILLS = {
    "python",
    "go",
    "golang",
    "java",
    "sql",
    "postgresql",
    "mysql",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "fastapi",
    "flask",
    "django",
    "linux",
    "redis",
    "nats",
    "rabbitmq",
    "kafka",
    "elasticsearch",
    "terraform",
    "git",
}
KNOWN_LANGUAGES = {"english", "vietnamese", "japanese", "korean", "french"}
ROLE_HINTS = {
    "backend": "Backend Engineer",
    "frontend": "Frontend Engineer",
    "fullstack": "Fullstack Engineer",
    "data engineer": "Data Engineer",
    "devops": "DevOps Engineer",
    "platform": "Platform Engineer",
    "software engineer": "Software Engineer",
}


def extract_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if suffix == ".docx":
        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError(f"Unsupported document type: {suffix}")


def parse_candidate_profile(text: str) -> dict:
    normalized = " ".join(text.split())
    lowered = normalized.lower()

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", normalized)
    phone_match = re.search(r"(\+?\d[\d\s().-]{7,}\d)", normalized)
    years_match = re.search(r"(\d+(?:\.\d+)?)\+?\s+years?", lowered)

    skills = sorted({skill for skill in KNOWN_SKILLS if re.search(rf"\b{re.escape(skill)}\b", lowered)})
    languages = sorted(
        {language.title() for language in KNOWN_LANGUAGES if re.search(rf"\b{language}\b", lowered)}
    )
    preferred_roles = sorted(
        {role for hint, role in ROLE_HINTS.items() if re.search(rf"\b{re.escape(hint)}\b", lowered)}
    )

    summary = normalized[:500] if normalized else None
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(1).strip() if phone_match else None,
        "years_experience": float(years_match.group(1)) if years_match else None,
        "skills": skills,
        "languages": languages,
        "preferred_roles": preferred_roles,
        "summary": summary,
    }

