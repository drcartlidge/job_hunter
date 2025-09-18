import requests
from bs4 import BeautifulSoup
from typing import List
from main import Job

def scrape_html(url: str, name: str, org: str = "") -> List[Job]:
    if "kahoot" in url.lower(): return scrape_kahoot(url, name)
    if "nearpod" in url.lower(): return scrape_nearpod(url, name)
    return scrape_generic(url, name)

def scrape_generic(url: str, name: str) -> List[Job]:
    jobs = []
    try:
        r = requests.get(url, timeout=30); r.raise_for_status()
        soup = BeautifulSoup(r.text,"html.parser")
        for a in soup.find_all("a", href=True):
            if "job" in a["href"].lower():
                title = a.get_text(strip=True)
                if not title: continue
                job_url = a["href"]
                if not job_url.startswith("http"): job_url = url.rstrip("/")+"/"+job_url.lstrip("/")
                jobs.append(Job(company=name,title=title,location="Unknown",url=job_url,description="Generic HTML job",raw={"href":a["href"]}))
    except Exception as e:
        print(f"[ERROR] HTML scrape failed for {name}: {e}")
    return jobs

def scrape_kahoot(url: str, name: str) -> List[Job]:
    jobs = []
    try:
        r = requests.get(url,timeout=30); r.raise_for_status()
        soup = BeautifulSoup(r.text,"html.parser")
        for a in soup.select("a[href*='careers/job']"):
            title = a.get_text(strip=True)
            job_url = a["href"]
            if not job_url.startswith("http"): job_url = "https://kahoot.com"+job_url
            jobs.append(Job(company=name,title=title,location="Unknown",url=job_url,description="Kahoot job",raw={"href":a["href"]}))
    except Exception as e:
        print(f"[ERROR] Kahoot scrape failed: {e}")
    return jobs

def scrape_nearpod(url: str, name: str) -> List[Job]:
    jobs = []
    try:
        r = requests.get(url,timeout=30); r.raise_for_status()
        soup = BeautifulSoup(r.text,"html.parser")
        for a in soup.select("a[href*='/jobs/']"):
            title = a.get_text(strip=True)
            job_url = a["href"]
            if not job_url.startswith("http"): job_url = "https://nearpod.com"+job_url
            jobs.append(Job(company=name,title=title,location="Unknown",url=job_url,description="Nearpod job",raw={"href":a["href"]}))
    except Exception as e:
        print(f"[ERROR] Nearpod scrape failed: {e}")
    return jobs
