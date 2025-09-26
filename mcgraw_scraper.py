# mcgraw_scraper.py
import requests
from typing import List
from models import Job

def scrape_mcgrawhill(url_api: str, name: str) -> List[Job]:
    """
    Scraper for McGraw Hill careers API.
    Example API endpoint:
    https://careers.mheducation.com/api/jobs?sortBy=relevance&descending=false&internal=false
    """
    jobs = []
    page = 1

    try:
        while True:
            url = f"{url_api}&page={page}"
            print(f"[DEBUG] Requesting McGraw Hill jobs (page={page})")  # <-- QC print
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print(f"[ERROR] McGraw Hill API request failed (page={page}): {r.status_code}")
                break

            data = r.json()
            items = data.get("jobs", [])
            if not items:
                print(f"[DEBUG] No jobs returned on page {page}, stopping.")  # <-- QC print
                break

            for i, item in enumerate(items):
                data = item.get("data", {})  # <-- unwrap the nested dict

                title = data.get("title", "")
                loc = data.get("full_location") or data.get("location_name", "")
                job_url = data.get("apply_url") or data.get("canonical_url")
                descr = data.get("description", "") or "No description."

                jobs.append(Job(
                    company=name,
                    title=title,
                    location=loc,
                    url=job_url,
                    description=descr,
                    raw=data
                ))

                if i < 3 and page == 1:
                    print(f"[DEBUG] Parsed job: {title} ({loc})")

            page += 1

    except Exception as e:
        print(f"[ERROR] McGraw Hill scrape failed: {e}")

    print(f"[INFO] Scraped {len(jobs)} McGraw Hill jobs total")  # <-- QC summary
    return jobs
