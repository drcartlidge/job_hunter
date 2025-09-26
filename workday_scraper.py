# workday_scraper.py
import requests
from typing import List
from urllib.parse import urlparse, urljoin
from models import Job

def _build_workday_api_url(public_url: str) -> str:
    """
    Convert a public Workday careers URL into the JSON jobs API endpoint.

    Examples:
      https://amplify.wd1.myworkdayjobs.com/Amplify_Careers
      https://renaissance.wd5.myworkdayjobs.com/en-US/Renaissance
      -> https://TENANT.wdX.myworkdayjobs.com/wday/cxs/TENANT/SITE/jobs
    """
    parsed = urlparse(public_url)
    host = parsed.netloc                       # e.g. amplify.wd1.myworkdayjobs.com
    tenant = host.split(".")[0]                # e.g. amplify

    # strip leading/trailing slashes and remove language segments like en-US
    parts = [p for p in parsed.path.strip("/").split("/") if p and "-" not in p]
    if not parts:
        raise ValueError(f"Could not derive Workday site from URL: {public_url}")
    site = parts[-1]                           # e.g. Amplify_Careers, Renaissance, External, Careers

    return f"https://{host}/wday/cxs/{tenant}/{site}/jobs", host


def scrape_workday(public_url: str, name: str) -> List[Job]:
    """
    Generic Workday scraper with:
      - robust API URL building
      - 422 auto-retry with expanded payload
      - duplicate detection to avoid infinite loops
      - page cap safety
      - debug logging
    """
    jobs: List[Job] = []
    seen_ids = set()
    page_cap = 50        # safety stop; adjust if a tenant truly has tons of jobs
    offset, limit = 0, 20
    pages = 0

    try:
        base_url, host = _build_workday_api_url(public_url)

        while True:
            # Start with lean payload; some tenants require expanded payload.
            payload = {"limit": limit, "offset": offset}
            print(f"[DEBUG] Requesting {name} jobs (offset={offset}, limit={limit})")
            print(f"[DEBUG] POST {base_url} payload={payload}")
            r = requests.post(base_url, json=payload, timeout=30)

            # Auto-retry on 422 with expanded payload
            if r.status_code == 422:
                payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
                print(f"[WARN] 422 from {name}. Retrying with expanded payload: {payload}")
                r = requests.post(base_url, json=payload, timeout=30)

            if r.status_code != 200:
                # show a slice of body for easier debugging
                body = r.text[:300].replace("\n", " ")
                print(f"[ERROR] Workday request failed for {name}: {r.status_code} {body}")
                break

            data = r.json()
            postings = data.get("jobPostings", [])
            print(f"[DEBUG] {name}: received {len(postings)} postings at offset={offset}")

            if not postings:
                break

            new_jobs = 0
            for i, p in enumerate(postings):
                # Choose a stable unique key
                job_id = p.get("externalPath") or p.get("id") or f"{p.get('title')}|{p.get('locationsText')}"
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = p.get("title", "") or ""
                location = p.get("locationsText", "") or ""
                job_url = urljoin(f"https://{host}/", p.get("externalPath", ""))
                descr = " • ".join(p.get("bulletFields", [])) or "No description."

                jobs.append(Job(
                    company=name,
                    title=title,
                    location=location,
                    url=job_url,
                    description=descr,
                    raw=p
                ))
                new_jobs += 1

                # Light QC for first page
                if offset == 0 and i < 3:
                    print(f"[DEBUG] Parsed job: {title} ({location})")

            # If this page produced no unique jobs, stop to avoid looping on recycled pages
            if new_jobs == 0:
                print(f"[DEBUG] No new unique postings at offset={offset}. Breaking.")
                break

            offset += limit
            pages += 1
            if pages >= page_cap:
                print(f"[WARN] Hit page cap ({page_cap}) for {name}. Stopping to avoid overfetch.")
                break

    except Exception as e:
        print(f"[ERROR] Workday scrape failed for {name}: {e}")

    print(f"[INFO] Scraped {len(jobs)} jobs from {name} (Workday)")
    return jobs
