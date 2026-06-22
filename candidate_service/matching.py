import re
from dataclasses import dataclass

from candidate_service.job_projection import ProjectedJob


MATCH_RULE_VERSION = "candidate-match-v1"


@dataclass(frozen=True)
class MatchResult:
    score: float
    score_breakdown: dict[str, float]
    matched_skills: list[str]
    missing_skills: list[str]


def score_candidate_job(profile: dict, job: ProjectedJob) -> MatchResult:
    candidate_skills = {skill.lower() for skill in profile.get("skills", [])}
    job_text = " ".join(filter(None, [job.title, job.description or "", job.employment_type or ""]))
    job_tokens = {token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]*", job_text)}
    matched_skills = sorted(candidate_skills & job_tokens)
    missing_skills = sorted(job_tokens & IMPORTANT_JOB_TOKENS.difference(candidate_skills))

    title_score = _title_score(profile.get("preferred_roles", []), job.title)
    skill_score = min(len(matched_skills) / max(len(candidate_skills), 1), 1.0)
    location_score = _location_score(profile.get("location"), job.location)
    experience_score = _experience_score(profile.get("years_experience"), job_text)

    breakdown = {
        "title": round(title_score * 40, 2),
        "skills": round(skill_score * 35, 2),
        "location": round(location_score * 15, 2),
        "experience": round(experience_score * 10, 2),
    }
    return MatchResult(
        score=round(sum(breakdown.values()), 2),
        score_breakdown=breakdown,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )


IMPORTANT_JOB_TOKENS = {
    "python",
    "go",
    "golang",
    "docker",
    "kubernetes",
    "fastapi",
    "django",
    "flask",
    "aws",
    "gcp",
    "terraform",
    "sql",
    "postgresql",
    "mysql",
    "redis",
}


def _title_score(preferred_roles: list[str], title: str) -> float:
    lowered_title = title.lower()
    if not preferred_roles:
        return 0.4
    for role in preferred_roles:
        if role.lower() in lowered_title:
            return 1.0
    return 0.2


def _location_score(candidate_location: str | None, job_location: str | None) -> float:
    if not job_location or not candidate_location:
        return 0.5
    if candidate_location.lower() in job_location.lower() or job_location.lower() in candidate_location.lower():
        return 1.0
    if "remote" in job_location.lower():
        return 0.8
    return 0.0


def _experience_score(years_experience: float | None, job_text: str) -> float:
    if years_experience is None:
        return 0.5
    required = re.search(r"(\d+(?:\.\d+)?)\+?\s+years?", job_text.lower())
    if not required:
        return 0.6
    required_years = float(required.group(1))
    return 1.0 if years_experience >= required_years else max(years_experience / required_years, 0.0)

