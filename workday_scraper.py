import requests
from typing import List
from main import Job

def scrape_workday(org: str, name: str) -> List[Job]:
    if name.lower().startswith("mcgraw"):
        return scrape_mcgrawhill(name)
    print(f"[INFO] Workday scraping not implemented for {name}.")
    return []

def scrape_mcgrawhill(name: str) -> List[Job]:
    jobs = []
    base_url = "https://mcgrawhill.wd5.myworkdayjobs.com/wday/cxs/mcgrawhill/External/jobs"
    offset, limit = 0, 20
    while True:
        payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
        r = requests.post(base_url, json=payload, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings: break
        for p in postings:
            title = p.get("title","")
            location = p.get("locationsText","")
            job_url = f"https://mcgrawhill.wd5.myworkdayjobs.com/en-US/External{p.get('externalPath','')}"
            descr = " • ".join(p.get("bulletFields", [])) or "No description."
            jobs.append(Job(company=name, title=title, location=location, url=job_url, description=descr, raw=p))
        offset += limit
    return jobs
