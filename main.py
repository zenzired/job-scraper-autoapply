import asyncio
import logging
from rich.console import Console
from rich.table import Table

from src.core.config import load_json_config, settings
from src.pipeline.schemas import CandidateProfile, RawScrapedJob
from src.scraper.engine import StealthScraperEngine
from src.scraper.parsers import JobParserRegistry
from src.pipeline.dedup import JobNormalizer
from src.matching.matcher import ResumeMatchEngine
from src.automation.form_filler import FormFillerAutomation

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("orchestrator")
console = Console()


async def run_pipeline(target_urls: list[str], dry_run: bool = True):
    """Executes the end-to-end scraper, normalization, matching, and auto-fill pipeline."""
    
    # 1. Load Candidate Profile from Private Submodule Config
    console.print("[bold blue]1. Loading candidate profile from private submodule...[/bold blue]")
    profile_data = load_json_config("candidate_profile.json")
    candidate_profile = CandidateProfile(**profile_data)
    console.print(f"[green]Loaded profile for: {candidate_profile.personal_info.first_name} {candidate_profile.personal_info.last_name}[/green]\n")

    # 2. Initialize Engines
    scraper_engine = StealthScraperEngine(headless=settings.HEADLESS_MODE)
    match_engine = ResumeMatchEngine(profile=candidate_profile)
    form_filler = FormFillerAutomation(profile=candidate_profile, dry_run=dry_run)

    results_table = Table(title="Job Pipeline Evaluation Results")
    results_table.add_column("Company", style="cyan")
    results_table.add_column("Title", style="bold white")
    results_table.add_column("Location", style="magenta")
    results_table.add_column("Match Score", style="green")
    results_table.add_column("Status", style="yellow")

    try:
        await scraper_engine.start()

        for url in target_urls:
            console.print(f"[bold yellow]Processing URL:[/bold yellow] {url}")

            # 3. Fetch Page Content via Stealth Playwright
            canonical_url, html_content = await scraper_engine.fetch_page_content(url)

            # 4. Parse HTML to RawScrapedJob
            raw_job: RawScrapedJob = JobParserRegistry.parse_html(
                url=url,
                canonical_url=canonical_url,
                html_content=html_content
            )

            # 5. Normalize Data & Deduplicate Hash
            cleaned_job = JobNormalizer.process_raw_job(raw_job)

            # 6. Evaluate Resume Match Score
            match_result = match_engine.evaluate_job(job_id=1, job=cleaned_job)

            # Render Table Row
            results_table.add_row(
                cleaned_job.company_name,
                cleaned_job.title,
                cleaned_job.raw_location or "N/A",
                f"{match_result.overall_match_score}%",
                match_result.recommendation.value
            )

            # 7. Form Filling Auto-Fill Trigger (If MATCHED and Dry-Run Enabled)
            if match_result.overall_match_score >= 70.0 and dry_run:
                console.print(f"[bold green]High match score detected! Executing Form Auto-Fill (Dry Run)...[/bold green]")
                await form_filler.auto_fill_job(cleaned_job.canonical_url)

    finally:
        await scraper_engine.close()

    console.print("\n", results_table)


if __name__ == "__main__":
    # Test sample URLs (Greenhouse / Lever sample postings)
    SAMPLE_TEST_URLS = [
        "https://boards.greenhouse.io/embed/job_app?token=4028328002",
    ]

    asyncio.run(run_pipeline(target_urls=SAMPLE_TEST_URLS, dry_run=True))