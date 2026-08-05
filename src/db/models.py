import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Float, DateTime, Enum, 
    ForeignKey, Index, Table, Column
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base ORM model providing standard declarative features."""
    pass


class ApplicationStatus(str, enum.Enum):
    """Tracks the state of a job through our application pipeline."""
    DISCOVERED = "DISCOVERED"          # Scraped and stored
    MATCHED = "MATCHED"                # High match score against resume
    PENDING_REVIEW = "PENDING_REVIEW"  # Waiting for human approval
    APPLIED = "APPLIED"                # Application submitted (or form auto-filled)
    REJECTED = "REJECTED"              # Rejected by employer
    IGNORED = "IGNORED"                # Low match score or manual ignore


# Association table linking jobs to skills (Many-to-Many)
job_skills = Table(
    "job_skills",
    Base.metadata,
    Column("job_id", Integer, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # URL Tracking
    job_url: Mapped[str] = mapped_column(Text, nullable=False)               # Original scraped link
    canonical_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # Direct ATS link after redirects
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)     # e.g., 'Greenhouse', 'Lever', 'Workday'
    
    # Deduplication Hash (md5 of normalized company + job title + job ID)
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    # Core Metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Compensation
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default="USD")
    
    # Timestamps
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    skills: Mapped[List["Skill"]] = relationship("Skill", secondary=job_skills, back_populates="jobs")
    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="job", uselist=False)

    __table_args__ = (
        Index("idx_company_title", "company_name", "title"),
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    jobs: Mapped[List[Job]] = relationship("Job", secondary=job_skills, back_populates="skills")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.DISCOVERED, nullable=False
    )
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Range 0.0 to 100.0
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job: Mapped[Job] = relationship("Job", back_populates="application")