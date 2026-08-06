from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from src.db.models import WorkplaceType, ApplicationStatus


# ==========================================
# 1. Candidate Profile Schemas
# ==========================================

class PersonalInfo(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_city: str
    current_state: Optional[str] = None
    country: str = "US"


class CandidateProfile(BaseModel):
    personal_info: PersonalInfo
    target_titles: List[str] = Field(
        ..., description="Job titles to match against, e.g. ['Python Developer', 'Backend Engineer']"
    )
    
    # Location & Workplace Preferences
    preferred_locations: List[str] = Field(
        default_factory=list, 
        description="Cities/Regions accepted, e.g. ['Austin, TX', 'New York, NY', 'Remote']"
    )
    allowed_workplace_types: List[WorkplaceType] = Field(
        default=[WorkplaceType.REMOTE, WorkplaceType.HYBRID],
        description="Accepted workplace modes"
    )
    
    skills: List[str] = Field(
        ..., description="List of core technical skills from your resume"
    )
    min_salary_expectation: Optional[int] = None
    resume_path: str = Field(..., description="Path to your master resume PDF/DOCX")
    resume_text_raw: str = Field(..., description="Plain text extracted from your resume for embedding/matching")


# ==========================================
# 2. Scraped Job Ingestion Schemas
# ==========================================

class RawScrapedJob(BaseModel):
    """Data shape directly extracted by Playwright / BeautifulSoup parsers."""
    job_url: str
    canonical_url: Optional[str] = None
    source_platform: str
    title: str
    company_name: str
    
    # Raw location fields
    raw_location: Optional[str] = None
    
    raw_description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = "USD"
    posted_at: Optional[datetime] = None


class CleanedJobData(BaseModel):
    """Normalized data ready for database insertion."""
    job_url: str
    canonical_url: Optional[str] = None
    source_platform: str
    dedup_hash: str
    
    title: str
    company_name: str
    
    # Structured Location Data
    raw_location: Optional[str] = None
    city: Optional[str] = None
    state_or_region: Optional[str] = None
    country: Optional[str] = "US"
    workplace_type: WorkplaceType = WorkplaceType.UNKNOWN
    
    raw_description: str
    extracted_skills: List[str] = Field(default_factory=list)
    
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = "USD"
    posted_at: Optional[datetime] = None


# ==========================================
# 3. Match Evaluation Result Schema
# ==========================================

class JobMatchResult(BaseModel):
    """Output from the matching engine comparing a Job against CandidateProfile."""
    job_id: int
    overall_match_score: float = Field(..., ge=0.0, le=100.0)
    title_score: float
    skill_score: float
    location_eligible: bool
    workplace_type_eligible: bool
    matched_skills: List[str]
    missing_skills: List[str]
    recommendation: ApplicationStatus