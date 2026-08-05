import re
import hashlib
from typing import Tuple, List, Optional
from slugify import slugify
from rapidfuzz import fuzz

from src.db.models import WorkplaceType
from src.pipeline.schemas import RawScrapedJob, CleanedJobData

# Core technical skills to auto-extract from job description text
KNOWN_SKILLS = [
    "python", "fastapi", "flask", "django", "linux", "docker", "kubernetes", 
    "windows", "postgresql", "mysql", "mongodb", "redis", "git", "aws", "azure", 
    "gcp", "terraform", "ansible", "playwright", "selenium", "bash", "powershell", 
    "rest api", "graphql", "ci/cd", "github actions", "sysadmin", "networking"
]


class JobNormalizer:
    """Cleans raw scraped job listings and extracts structured location, modality, and skills."""

    @staticmethod
    def generate_dedup_hash(company_name: str, title: str, raw_location: Optional[str] = None) -> str:
        """
        Creates a deterministic MD5 hash based on normalized company, title, and location.
        Guarantees that identical job postings generate identical hashes.
        """
        norm_company = slugify(company_name)
        norm_title = slugify(title)
        norm_loc = slugify(raw_location) if raw_location else "any"
        
        raw_identifier = f"{norm_company}:{norm_title}:{norm_loc}"
        return hashlib.md5(raw_identifier.encode("utf-8")).hexdigest()

    @staticmethod
    def parse_workplace_type(raw_text: str) -> WorkplaceType:
        """Detects whether a job is REMOTE, HYBRID, or ON_SITE from text snippets."""
        text_lower = raw_text.lower()

        if re.search(r"\b(remote|work from home|wfh|telecommute)\b", text_lower):
            if re.search(r"\b(hybrid|in-office|days in office)\b", text_lower):
                return WorkplaceType.HYBRID
            return WorkplaceType.REMOTE
        elif re.search(r"\b(hybrid|flexible|in-office \d days)\b", text_lower):
            return WorkplaceType.HYBRID
        elif re.search(r"\b(on-site|onsite|in-office|in person)\b", text_lower):
            return WorkplaceType.ON_SITE
        
        return WorkplaceType.UNKNOWN

    @staticmethod
    def parse_location(raw_location: Optional[str]) -> Tuple[Optional[str], Optional[str], str, WorkplaceType]:
        """
        Parses raw location strings like 'Adelaide, SA (Hybrid)' into:
        (city, state_or_region, country, workplace_type)
        """
        if not raw_location:
            return None, None, "AU", WorkplaceType.UNKNOWN

        workplace_type = JobNormalizer.parse_workplace_type(raw_location)

        # Clean string: strip parentheses content e.g. "Adelaide (Hybrid)" -> "Adelaide"
        clean_loc = re.sub(r"\(.*?\)", "", raw_location).strip()
        parts = [p.strip() for p in clean_loc.split(",") if p.strip()]

        city = None
        state = None
        country = "AU"

        if len(parts) >= 2:
            city = parts[0]
            state = parts[1]
        elif len(parts) == 1:
            loc_lower = parts[0].lower()
            if loc_lower in ["remote", "work from home", "wfh"]:
                workplace_type = WorkplaceType.REMOTE
            elif loc_lower in ["adelaide", "perth", "sydney", "melbourne", "brisbane"]:
                city = parts[0]
            elif loc_lower in ["sa", "south australia", "wa", "western australia", "nsw", "vic", "qld"]:
                state = parts[0]
            else:
                city = parts[0]

        return city, state, country, workplace_type

    @staticmethod
    def extract_skills(description: str) -> List[str]:
        """Scans the job description text for technical skill keywords."""
        found_skills = set()
        desc_lower = description.lower()

        for skill in KNOWN_SKILLS:
            # Match exact word boundaries so 'git' doesn't match inside 'digital'
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, desc_lower):
                found_skills.add(skill.title())

        return sorted(list(found_skills))

    @classmethod
    def process_raw_job(cls, raw_job: RawScrapedJob) -> CleanedJobData:
        """Transforms a RawScrapedJob object into CleanedJobData ready for database storage."""
        
        # Combine title, raw location, and top description to catch modality clues
        combined_text = f"{raw_job.title} {raw_job.raw_location or ''} {raw_job.raw_description[:1000]}"
        workplace_type = cls.parse_workplace_type(combined_text)

        # Parse city & state
        city, state, country, loc_workplace = cls.parse_location(raw_job.raw_location)
        
        if loc_workplace != WorkplaceType.UNKNOWN:
            workplace_type = loc_workplace

        # Extract skills & generate hash
        skills = cls.extract_skills(raw_job.raw_description)
        dedup_hash = cls.generate_dedup_hash(
            company_name=raw_job.company_name,
            title=raw_job.title,
            raw_location=raw_job.raw_location
        )

        return CleanedJobData(
            job_url=raw_job.job_url,
            canonical_url=raw_job.canonical_url,
            source_platform=raw_job.source_platform,
            dedup_hash=dedup_hash,
            title=raw_job.title,
            company_name=raw_job.company_name,
            raw_location=raw_job.raw_location,
            city=city,
            state_or_region=state,
            country=country,
            workplace_type=workplace_type,
            raw_description=raw_job.raw_description,
            extracted_skills=skills,
            salary_min=raw_job.salary_min,
            salary_max=raw_job.salary_max,
            currency=raw_job.currency,
            posted_at=raw_job.posted_at
        )


class FuzzyDeduplicator:
    """Fuzzy matching helper to compare similar job titles."""

    @staticmethod
    def is_similar_title(title_a: str, title_b: str, threshold: float = 85.0) -> bool:
        """Returns True if two titles match above the token-sort threshold."""
        ratio = fuzz.token_sort_ratio(title_a.lower(), title_b.lower())
        return ratio >= threshold