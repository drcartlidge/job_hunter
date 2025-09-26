# icims_scraper.py
import requests
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from models import Job

def scrape_icims(url: str, name: str) -> List[Job]:
    """
    Scrapes McGraw Hill’s iCIMS careers page (careers.mheducation.com/jobs).
    """
    jobs = []
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # On McGraw Hill’s site, each job row is an <a> under a <div class="job-card__title"> (or similar).
        # Let’s look for links under job listing containers:
        for link in soup.select("a.jobCard__link, a.job-card__title, a.jobTitle"):  # try multiple possible classes
            title = link.get_text(strip=True)
            href = link.get("href")
            if not href:
                continue
            job_url = href if href.startswith("http") else urljoin(url, href)

            # Try to find location: the next sibling or parent elements often have a <div> with location
            parent = link.parent
            loc_elem = parent.select_one(".jobCard__location, .job-card__location, .location")
            location = loc_elem.get_text(strip=True) if loc_elem else None

            jobs.append(Job(
                company=name,
                title=title,
                location=location,
                url=job_url,
                description="(from iCIMS listing page)",
                raw={"html": str(link)}
            ))

        print(f"[INFO] Scraped {len(jobs)} jobs from {name} (iCIMS)")
    except Exception as e:
        print(f"[ERROR] ICIMS scrape failed for {name}: {e}")

    return jobs
