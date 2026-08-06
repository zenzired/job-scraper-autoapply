from bs4 import BeautifulSoup
from src.pipeline.schemas import RawScrapedJob

class GreenhouseParser:
    @staticmethod
    def parse(url: str, canonical_url: str, html_content: str) -> RawScrapedJob:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract Job Title
        title_elem = soup.find("h1", class_="app-title") or soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

        # Extract Company Name
        company_elem = soup.find("span", class_="company-name") or soup.find("a", id="logo")
        company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"

        # Extract Location
        location_elem = soup.find("div", class_="location") or soup.find("span", class_="location")
        location = location_elem.get_text(strip=True) if location_elem else None

        # Extract Description
        desc_elem = soup.find("div", id="content") or soup.find("body")
        description = desc_elem.get_text(separator="\n", strip=True) if desc_elem else ""

        return RawScrapedJob(
            url=url,
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
        
        # Fallback generic parser
        soup = BeautifulSoup(html_content, "html.parser")
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Unknown Title"
        body = soup.find("body").get_text(separator="\n", strip=True) if soup.find("body") else ""
        
        return RawScrapedJob(
            url=url,
            canonical_url=canonical_url,
            source_platform="Generic",
            title=title,
            company_name="Unknown Company",
            raw_description=body
        )