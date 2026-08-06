import logging
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.pipeline.schemas import RawScrapedJob

logger = logging.getLogger("job_parser")


class GreenhouseParser:
    @staticmethod
    def parse(url: str, canonical_url: str, html_content: str) -> RawScrapedJob:
        soup = BeautifulSoup(html_content, "html.parser")

        # --- 1. Company Name Extraction ---
        company = "Unknown Company"
        og_site = soup.find("meta", attrs={"property": "og:site_name"}) or soup.find("meta", attrs={"name": "og:site_name"})
        
        if og_site and og_site.get("content"):
            company = og_site["content"].strip()
        else:
            company_elem = (
                soup.find("span", class_="company-name")
                or soup.find("a", class_="logo")
                or soup.find("div", id="header")
                or soup.find("span", id="sub-header")
            )
            if company_elem:
                text = company_elem.get_text(strip=True)
                if "at " in text.lower():
                    company = text.split("at ")[-1].strip()
                elif text:
                    company = text

        # Clean fallback extraction from path: strip query parameters like ?error=true
        if company == "Unknown Company" or "?" in company:
            parsed_path = urlparse(canonical_url).path.strip("/")
            parts = [p for p in parsed_path.split("/") if p and p not in ["embed", "jobs", "job_app"]]
            if parts:
                company = parts[0].capitalize()

        # Final sanity check: strip query strings if captured
        if "?" in company:
            company = company.split("?")[0].capitalize()

        # --- 2. Job Title Extraction ---
        title = ""
        og_title = soup.find("meta", attrs={"property": "og:title"}) or soup.find("meta", attrs={"name": "og:title"})
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()

        if not title:
            title_elem = (
                soup.find("h1", class_="app-title")
                or soup.find("h1", id="header-title")
                or soup.find("h1")
                or soup.find("title")
            )
            if title_elem:
                title = title_elem.get_text(strip=True)

        # Strip redundant company suffix from title
        if company and company != "Unknown Company" and f" at {company}" in title:
            title = title.replace(f" at {company}", "").strip()

        # --- 3. Location Extraction ---
        location = None
        location_elem = (
            soup.find("div", class_="location")
            or soup.find("span", class_="location")
            or soup.find("div", class_="app-location")
        )
        if location_elem:
            location = location_elem.get_text(strip=True)

        # --- 4. Description Extraction ---
        desc_elem = (
            soup.find("div", id="content")
            or soup.find("div", id="main")
            or soup.find("body")
        )
        description = desc_elem.get_text(separator="\n", strip=True) if desc_elem else ""

        logger.info(f"Parsed Greenhouse Job - Title: '{title}', Company: '{company}', Location: '{location}'")

        return RawScrapedJob(
            job_url=url,
            canonical_url=canonical_url,
            source_platform="Greenhouse",
            title=title or "Unknown Title",
            company_name=company,
            raw_location=location,
            raw_description=description,
        )


class JobParserRegistry:
    @staticmethod
    def parse_html(url: str, canonical_url: str, html_content: str) -> RawScrapedJob:
        if "greenhouse.io" in url or "greenhouse.io" in canonical_url:
            return GreenhouseParser.parse(url, canonical_url, html_content)

        soup = BeautifulSoup(html_content, "html.parser")
        title_elem = soup.find("h1") or soup.find("title")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
        body = soup.find("body").get_text(separator="\n", strip=True) if soup.find("body") else ""

        return RawScrapedJob(
            job_url=url,
            canonical_url=canonical_url,
            source_platform="Generic",
            title=title,
            company_name="Unknown Company",
            raw_description=body,
        )