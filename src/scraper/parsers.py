from bs4 import BeautifulSoup
from src.pipeline.schemas import RawScrapedJob


class GreenhouseParser:
    @staticmethod
    def parse(url: str, canonical_url: str, html_content: str) -> RawScrapedJob:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Job Title
        title_elem = (
            soup.find("h1", class_="app-title")
            or soup.find("h1", id="header-title")
            or soup.find("h1")
        )
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

        # 2. Company Name
        company_elem = (
            soup.find("span", class_="company-name")
            or soup.find("a", class_="logo")
            or soup.find("div", id="header")
        )
        company = "Unknown Company"
        if company_elem:
            text = company_elem.get_text(strip=True)
            if "at " in text.lower():
                company = text.split("at ")[-1].strip()
            elif text:
                company = text

        # 3. Location
        location_elem = (
            soup.find("div", class_="location")
            or soup.find("span", class_="location")
            or soup.find("div", class_="app-location")
        )
        location = location_elem.get_text(strip=True) if location_elem else None

        # 4. Description
        desc_elem = (
            soup.find("div", id="content")
            or soup.find("div", id="main")
            or soup.find("body")
        )
        description = desc_elem.get_text(separator="\n", strip=True) if desc_elem else ""

        return RawScrapedJob(
            job_url=url,
            canonical_url=canonical_url,
            source_platform="Greenhouse",
            title=title,
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
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Unknown Title"
        body = soup.find("body").get_text(separator="\n", strip=True) if soup.find("body") else ""

        return RawScrapedJob(
            job_url=url,
            canonical_url=canonical_url,
            source_platform="Generic",
            title=title,
            company_name="Unknown Company",
            raw_description=body,
        )