import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class WorkplaceType(str, enum.Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ON_SITE = "ON_SITE"
    UNKNOWN = "UNKNOWN"


class ApplicationStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    MATCHED = "MATCHED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPLIED = "APPLIED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"


class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dedup_hash: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    job_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state_or_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(10), default="AU")
    workplace_type: Mapped[WorkplaceType] = mapped_column(
        Enum(WorkplaceType, native_enum=False), default=WorkplaceType.UNKNOWN
    )

    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False), default=ApplicationStatus.DISCOVERED
    )
    overall_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)