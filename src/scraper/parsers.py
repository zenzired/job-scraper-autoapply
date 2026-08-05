import re
from typing import Optional
from bs4 import BeautifulSoup
from src.pipeline.schemas import RawScrapedJob


class JobParserRegistry:
    """Routes job posting HTML to the appropriate ATS-specific parser or fallback parser."""

    @staticmethod
    def parse_html(url: str, canonical_url: str, html_content: str) -> RawScrapedJob:
        """Determines the platform from URL patterns and parses the HTML into RawScrapedJob."""
        soup = BeautifulSoup(html_content, "html.parser")
        target_url = canonical_url or url

        if "greenhouse.io" in target_url:
            return JobParserRegistry._parse_greenhouse(url, canonical_url, soup)
        elif "lever.co" in target_url:
            return JobParserRegistry._parse_lever(url, canonical_url, soup)
        else:
            return JobParserRegistry._parse_generic(url, canonical_url, soup)

    @staticmethod
    def _parse_greenhouse(url: str, canonical_url: str, soup: BeautifulSoup) -> RawScrapedJob:
        """Parser for Greenhouse ATS postings."""
        title_elem = soup.find("h1", class_="app-title") or soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

        # Greenhouse company name is usually in a company header or title tag
        company_elem = soup.find("span", class_="company-name") or soup.find("title")
        company_name = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
        if "at " in company_name.lower():
            company_name = company_name.split("at ")[-1].strip()

        location_elem = soup.find("div", class_="location") or soup.find("span", class_="location")
        raw_location = location_elem.get_text(strip=True) if location_elem else None

        # Content container
        content_elem = soup.find("div", id="content") or soup.body
        raw_description = content_elem.get_text(separator="\n", strip=True) if content_elem else ""

        return RawScrapedJob(
            job_url=url,
            canonical_url=canonical_url,
            source_platform="Greenhouse",
            title=title,
            company_name=company_name,
            raw_location=raw_location,
            raw_description=raw_description
        )

    @staticmethod
    def _parse_lever(url: str, canonical_url: str, soup: BeautifulSoup) -> RawScrapedJob:
        """Parser for Lever ATS postings."""
        title_elem = soup.find("h2") or soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

        company_name = "Unknown Company"
        # Lever page headers usually have "Company Name - Job Title" in <title>
        if soup.title:
            title_text = soup.title.get_text(strip=True)
            if " - " in title_text:
                company_name = title_text.split(" - ")[0].strip()

        location_elem = soup.find("div", class_="location") or soup.find("span", class_="workplaceTypes")
        raw_location = location_elem.get_text(strip=True) if location_elem else None

        content_elem = soup.find("div", class_="content-wrapper") or soup.body
        raw_description = content_elem.get_text(separator="\n", strip=True) if content_elem else ""

        return RawScrapedJob(
            job_url=url,
            canonical_url=canonical_url,
            source_platform="Lever",
            title=title,
            company_name=company_name,
            raw_location=raw_location,
            raw_description=raw_description
        )

    @staticmethod
    def _parse_generic(url: str, canonical_url: str, soup: BeautifulSoup) -> RawScrapedJob:
        """Fallback parser using semantic HTML tags for custom company career pages."""
        title_elem = soup.find("h1") or soup.find("title")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

        company_name = "Unknown Company"
        if soup.title:
            company_name = soup.title.get_text(strip=True).split("|")[0].split("-")[0].strip()

        # Try to find location using common class names or keywords
        location_elem = (
            soup.find(class_=re.compile(r"location|job-location|address", re.I)) or
            soup.find(string=re.compile(r"remote|hybrid|on-site|adelaide|perth", re.I))
        )
        raw_location = location_elem.get_text(strip=True) if hasattr(location_elem, "get_text") else str(location_elem or "")

        # Extract main body text
        main_body = soup.find("main") or soup.find("article") or soup.body
        raw_description = main_body.get_text(separator="\n", strip=True) if main_body else ""

        return RawScrapedJob(
            job_url=url,
            canonical_url=canonical_url,
            source_platform="Generic",
            title=title,
            company_name=company_name,
            raw_location=raw_location if raw_location else None,
            raw_description=raw_description
        )