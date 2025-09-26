import requests
from bs4 import BeautifulSoup
from typing import List
from models import Job
import json

def scrape_html(url: str, name: str, org: str = "") -> List[Job]:
    """
    Dispatcher for HTML-based scrapers.
    """
    if "kahoot" in url.lower():
        return scrape_kahoot(url, name)
    if "nearpod" in url.lower():
        return scrape_nearpod(url, name)
    if "workdayjobs.com" in url.lower():
        return scrape_workday_html(url, name)
    if "dayforcehcm.com" in url.lower() and "k12l" in url.lower():
        return scrape_savvas(url, name)
    return scrape_generic(url, name)


def scrape_generic(url: str, name: str) -> List[Job]:
    """
    Very broad fallback HTML scraper: finds any <a> with 'job' in the href.
    """
    jobs = []
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if "job" in a["href"].lower():
                title = a.get_text(strip=True)
                if not title:
                    continue
                job_url = a["href"]
                if not job_url.startswith("http"):
                    job_url = url.rstrip("/") + "/" + job_url.lstrip("/")
                jobs.append(Job(
                    company=name,
                    title=title,
                    location="Unknown",
                    url=job_url,
                    description="Generic HTML job",
                    raw={"href": a["href"]}
                ))
        print(f"[INFO] Scraped {len(jobs)} jobs from {name} (generic HTML)")
    except Exception as e:
        print(f"[ERROR] HTML scrape failed for {name}: {e}")
    return jobs


def scrape_kahoot(url: str, name: str) -> List[Job]:
    """
    Kahoot careers page scraper.
    """
    jobs = []
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href*='careers/job']"):
            title = a.get_text(strip=True)
            job_url = a["href"]
            if not job_url.startswith("http"):
                job_url = "https://kahoot.com" + job_url
            jobs.append(Job(
                company=name,
                title=title,
                location="Unknown",
                url=job_url,
                description="Kahoot job",
                raw={"href": a["href"]}
            ))
        print(f"[INFO] Scraped {len(jobs)} jobs from {name} (Kahoot)")
    except Exception as e:
        print(f"[ERROR] Kahoot scrape failed: {e}")
    return jobs


def scrape_nearpod(url: str, name: str) -> List[Job]:
    """
    Nearpod careers page scraper.
    """
    jobs = []
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href*='/jobs/']"):
            title = a.get_text(strip=True)
            job_url = a["href"]
            if not job_url.startswith("http"):
                job_url = "https://nearpod.com" + job_url
            jobs.append(Job(
                company=name,
                title=title,
                location="Unknown",
                url=job_url,
                description="Nearpod job",
                raw={"href": a["href"]}
            ))
        print(f"[INFO] Scraped {len(jobs)} jobs from {name} (Nearpod)")
    except Exception as e:
        print(f"[ERROR] Nearpod scrape failed: {e}")
    return jobs


def scrape_workday_html(url: str, name: str) -> List[Job]:
    """
    Workday HTML scraper for tenants like Chegg and Renaissance
    that block the JSON API but still render jobs in the page HTML.
    """
    jobs = []
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Workday uses <a data-automation-id="jobTitle"> for job links
        for a in soup.select("a[data-automation-id='jobTitle']"):
            title = a.get_text(strip=True)
            job_url = a.get("href")
            if job_url and not job_url.startswith("http"):
                job_url = url.rstrip("/") + "/" + job_url.lstrip("/")

            # Sometimes the location is in the sibling <div>
            location_tag = a.find_parent("div").find_next_sibling("div")
            loc = location_tag.get_text(strip=True) if location_tag else "Unknown"

            jobs.append(Job(
                company=name,
                title=title,
                location=loc,
                url=job_url,
                description="Workday HTML job",
                raw={"href": job_url, "title": title, "location": loc}
            ))

        print(f"[INFO] Scraped {len(jobs)} jobs from {name} (Workday HTML)")

    except Exception as e:
        print(f"[ERROR] Workday HTML scrape failed for {name}: {e}")

    return jobs


import requests
from bs4 import BeautifulSoup
from typing import List
from models import Job


def scrape_savvas(url: str, name: str) -> List[Job]:
    """
    Scraper for Savvas Learning (DayforceHCM).
    Extracts jobs from the embedded Next.js __NEXT_DATA__ JSON.
    """
    jobs = []
    try:
        print(f"[DEBUG] Fetching Savvas careers page: {url}")
        r = requests.get(url, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # Find Next.js embedded JSON
        next_data = soup.find("script", id="__NEXT_DATA__")
        if not next_data:
            print("[ERROR] Could not find __NEXT_DATA__ script in Savvas page")
            return jobs

        data = json.loads(next_data.string)

        # Step 1: Navigate into pageProps.dehydratedState
        props = data.get("props", {})
        page_props = props.get("pageProps", {})
        dehydrated = page_props.get("dehydratedState", {})
        queries = dehydrated.get("queries", [])

        print(f"[DEBUG] Found {len(queries)} dehydrated queries")

        # Step 2: loop through all queries
        for idx, q in enumerate(queries):
            state = q.get("state", {})
            inner_data = state.get("data", {})
            if not inner_data:
                continue

            print(f"[DEBUG] Query {idx} keys: {list(inner_data.keys())}")

            postings = (
                inner_data.get("jobs")
                or inner_data.get("jobPostings")
                or inner_data.get("items")
                or inner_data.get("jobPostingsBySearch")
                or []
            )

            if postings and isinstance(postings, list):
                print(f"[DEBUG] Found {len(postings)} postings in query {idx}")
                for p in postings:
                    title = p.get("title") or p.get("jobTitle") or "Unknown"
                    location = p.get("shortLocation") or p.get("location") or "Unknown"
                    job_url = (
                        p.get("canonical_url")
                        or p.get("apply_url")
                        or url
                    )
                    descr = (
                        p.get("description")
                        or p.get("jobDescription")
                        or "No description."
                    )

                    jobs.append(Job(
                        company=name,
                        title=title,
                        location=location,
                        url=job_url,
                        description=descr,
                        raw=p
                    ))

        if not jobs:
            print("[WARN] No jobs found in Savvas JSON, falling back to HTML scrape")
            for h2 in soup.select("h2[test-id='job-title']"):
                title = h2.get_text(strip=True)
                if not title:
                    continue
                jobs.append(Job(
                    company=name,
                    title=title,
                    location="Unknown",
                    url=url,
                    description="Scraped from HTML fallback",
                    raw={"text": title}
                ))

    except Exception as e:
        print(f"[ERROR] Savvas scrape failed: {e}")

    return jobs






