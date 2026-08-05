import asyncio
import random
import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stealth_scraper")

# Modern Desktop User Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


class StealthScraperEngine:
    """Manages an async Playwright browser instance with anti-bot stealth configurations."""

    def __init__(self, headless: bool = True, max_delay: float = 3.0):
        self.headless = headless
        self.max_delay = max_delay
        self.playwright = None
        self.browser: Optional[Browser] = None

    async def start(self):
        """Initializes the Playwright driver and launches Chromium."""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                ]
            )
            logger.info("Playwright Chromium engine started successfully.")

    async def create_stealth_context(self) -> BrowserContext:
        """Creates an isolated browser context with randomized user-agent and stealth scripts."""
        if not self.browser:
            await self.start()

        user_agent = random.choice(USER_AGENTS)
        context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
            locale="en-US,en;q=0.9",
            timezone_id="Australia/Adelaide",
        )
        return context

    async def fetch_page_content(self, url: str) -> tuple[str, str]:
        """
        Navigates to a target URL with humanized delays and stealth masking.
        Returns a tuple of (final_canonical_url, page_html_content).
        """
        context = await self.create_stealth_context()
        page: Page = await context.new_page()

        # Apply stealth patches to bypass navigator.webdriver detection
        await stealth_async(page)

        try:
            logger.info(f"Navigating to: {url}")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Introduce humanized random delay
            sleep_time = random.uniform(1.5, self.max_delay)
            await asyncio.sleep(sleep_time)

            # Smooth scroll down to simulate human reading and trigger lazy-loaded dynamic content
            await page.evaluate("window.scrollBy(0, 500);")
            await asyncio.sleep(0.5)

            final_url = page.url
            content = await page.content()
            logger.info(f"Successfully fetched content from: {final_url}")
            return final_url, content

        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {str(e)}")
            raise e
        finally:
            await page.close()
            await context.close()

    async def close(self):
        """Cleanly shuts down the browser instance."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright engine closed.")