from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

from src.db.models import WorkplaceType, ApplicationStatus
from src.pipeline.schemas import CandidateProfile, CleanedJobData, JobMatchResult


class ResumeMatchEngine:
    """Evaluates job postings against a candidate profile using TF-IDF and heuristic filters."""

    def __init__(self, profile: CandidateProfile):
        self.profile = profile
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))

    def calculate_text_similarity(self, job_description: str) -> float:
        """Computes TF-IDF Cosine Similarity between resume raw text and job description."""
        if not self.profile.resume_text_raw or not job_description:
            return 0.0

        try:
            tfidf_matrix = self.vectorizer.fit_transform([self.profile.resume_text_raw, job_description])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return round(float(similarity) * 100, 2)
        except Exception:
            return 0.0

    def calculate_title_score(self, job_title: str) -> float:
        """Evaluates fuzzy match ratio of job title against candidate's target job titles."""
        best_score = 0.0
        job_title_lower = job_title.lower()

        for target in self.profile.target_titles:
            score = fuzz.token_set_ratio(target.lower(), job_title_lower)
            if score > best_score:
                best_score = float(score)

        return best_score

    def calculate_skill_overlap(self, job_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """Calculates skill match ratio and returns lists of matched vs missing skills."""
        if not job_skills:
            return 50.0, [], []

        candidate_skills_set = {s.lower() for s in self.profile.skills}
        matched = []
        missing = []

        for skill in job_skills:
            if skill.lower() in candidate_skills_set:
                matched.append(skill)
            else:
                missing.append(skill)

        skill_score = (len(matched) / len(job_skills)) * 100.0 if job_skills else 0.0
        return round(skill_score, 2), matched, missing

    def check_location_eligibility(self, job: CleanedJobData) -> bool:
        """Determines if job location satisfies candidate preferred location constraints."""
        if job.workplace_type == WorkplaceType.REMOTE and WorkplaceType.REMOTE in self.profile.allowed_workplace_types:
            return True

        if not self.profile.preferred_locations:
            return True

        job_location_str = f"{job.city or ''} {job.state_or_region or ''} {job.raw_location or ''}".lower()

        for pref_loc in self.profile.preferred_locations:
            pref_clean = pref_loc.lower().strip()
            if pref_clean in job_location_str or (job.city and pref_clean in job.city.lower()):
                return True

        return False

    def check_workplace_eligibility(self, job: CleanedJobData) -> bool:
        """Verifies if job workplace modality (REMOTE, HYBRID, ON_SITE) is allowed."""
        if job.workplace_type == WorkplaceType.UNKNOWN:
            return True
        return job.workplace_type in self.profile.allowed_workplace_types

    def evaluate_job(self, job_id: int, job: CleanedJobData) -> JobMatchResult:
        """Main evaluation method: calculates weighted overall score and determines status."""
        location_eligible = self.check_location_eligibility(job)
        workplace_eligible = self.check_workplace_eligibility(job)

        title_score = self.calculate_title_score(job.title)
        skill_score, matched_skills, missing_skills = self.calculate_skill_overlap(job.extracted_skills)
        text_similarity = self.calculate_text_similarity(job.raw_description)

        overall_score = round((title_score * 0.40) + (text_similarity * 0.35) + (skill_score * 0.25), 2)

        if not location_eligible or not workplace_eligible:
            recommendation = ApplicationStatus.IGNORED
        elif overall_score >= 75.0:
            recommendation = ApplicationStatus.MATCHED
        elif overall_score >= 50.0:
            recommendation = ApplicationStatus.PENDING_REVIEW
        else:
            recommendation = ApplicationStatus.IGNORED

        return JobMatchResult(
            job_id=job_id,
            overall_match_score=overall_score,
            title_score=title_score,
            skill_score=skill_score,
            location_eligible=location_eligible,
            workplace_type_eligible=workplace_eligible,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            recommendation=recommendation
        )