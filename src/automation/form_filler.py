import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Page
from src.pipeline.schemas import CandidateProfile

logger = logging.getLogger("form_filler")


class FormFillerAutomation:
    """Automates form population on ATS sites (Greenhouse, Lever) with dry-run protection."""

    def __init__(self, profile: CandidateProfile, dry_run: bool = True):
        self.profile = profile
        self.dry_run = dry_run

    async def fill_greenhouse_form(self, page: Page):
        """Fills standard input fields on a Greenhouse application page."""
        logger.info("Filling Greenhouse form fields...")

        # Basic candidate details
        await page.fill("input[id='first_name']", self.profile.personal_info.first_name)
        await page.fill("input[id='last_name']", self.profile.personal_info.last_name)
        await page.fill("input[id='email']", self.profile.personal_info.email)
        await page.fill("input[id='phone']", self.profile.personal_info.phone)

        # Attach Resume if PDF file path exists on disk
        resume_file = Path(self.profile.resume_path)
        if resume_file.exists():
            file_input = await page.query_selector("input[type='file']")
            if file_input:
                await file_input.set_input_files(str(resume_file.resolve()))
                logger.info(f"Attached resume from: {resume_file.resolve()}")

        # Highlight submission button visually for dry-run inspection without clicking
        submit_btn = await page.query_selector("input[type='submit'], button[type='submit']")
        if submit_btn:
            await submit_btn.evaluate("el => el.style.border = '4px solid red'")

        logger.info("Form filled successfully.")

        if self.dry_run:
            logger.info("[DRY RUN MODE] Stopping before submitting the application.")
            await asyncio.sleep(5)  # Pause for human visual verification

    async def auto_fill_job(self, apply_url: str):
        """Launches a Playwright browser session for visual form filling."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible browser window
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(apply_url, wait_until="domcontentloaded")
                await self.fill_greenhouse_form(page)
            finally:
                await browser.close()