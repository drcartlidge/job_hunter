import os
import smtplib
import json
import requests
import pandas as pd
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from models import Job

load_dotenv()  # load .env config

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")  # string, cast later if needed
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ONLY_US_ROLES = os.getenv("ONLY_US_ROLES")  # e.g., "true"/"false"
MIN_MATCH_SCORE = os.getenv("MIN_MATCH_SCORE")  # string, cast later if needed

# Convert certain vars to expected types
SMTP_PORT = int(SMTP_PORT) if SMTP_PORT else None
MIN_MATCH_SCORE = float(MIN_MATCH_SCORE) if MIN_MATCH_SCORE else None
ONLY_US_ROLES = ONLY_US_ROLES.lower() == "true" if ONLY_US_ROLES else False

# -------------------------
# Job dataclass
# -------------------------
@dataclass
class Job:
    company: str
    title: str
    location: Optional[str]
    url: str
    description: str
    raw: Dict[str, Any]


# -------------------------
# Baseline filter
# -------------------------
def baseline_title_filter(job: Job) -> bool:
    # Broad filter with smarter 'researcher' handling
    KEYWORDS = [
        "data","machine","ml","ai","analytics","insights","quant","science",
        "research scientist","measurement","psychometric","assessment","statistician"
    ]
    title = job.title.lower()
    if any(k in title for k in KEYWORDS):
        return True
    if "researcher" in title and any(x in title for x in [
        "data","quant","ml","ai","analytics","psychometric","assessment"
    ]):
        return True
    return False


# -------------------------
# Resume loader
# -------------------------
def load_resume(path="data/resume.txt") -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# -------------------------
# Greenhouse scraper
# -------------------------
def scrape_greenhouse(org: str, name: str) -> List[Job]:
    jobs = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        for j in data.get("jobs", []):
            jobs.append(Job(
                company=name,
                title=j.get("title", ""),
                location=(j.get("location") or {}).get("name", ""),
                url=j.get("absolute_url", ""),
                description=j.get("content", ""),
                raw=j
            ))
    except Exception as e:
        print(f"[ERROR] Greenhouse scrape failed for {name}: {e}")
    return jobs


# -------------------------
# Lever scraper
# -------------------------
def scrape_lever(org: str, name: str) -> List[Job]:
    def safe_join(value):
        """Normalize Lever fields into a comma-separated string."""
        if isinstance(value, list):
            return ", ".join([str(x) for x in value if x])
        return str(value) if value else ""

    jobs = []
    url = f"https://api.lever.co/v0/postings/{org}?mode=json"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        for j in r.json():
            categories = j.get("categories", {})

            # normalize each category field
            location = safe_join(categories.get("location"))
            team = safe_join(categories.get("team"))
            commitment = safe_join(categories.get("commitment"))

            jobs.append(Job(
                company=name,
                title=j.get("text", ""),
                location=", ".join([x for x in [location, team, commitment] if x]),
                url=j.get("hostedUrl", ""),
                description=j.get("descriptionPlain", ""),
                raw=j
            ))
    except Exception as e:
        print(f"[ERROR] Lever scrape failed for {name}: {e}")
    return jobs



# -------------------------
# Workday scraper (dispatcher)
# -------------------------
from workday_scraper import scrape_workday

# -------------------------
# HTML scraper (dispatcher)
# -------------------------
from html_scraper import scrape_html


# -------------------------
# Rank jobs with LLM
# -------------------------
def rank_jobs_with_llm(jobs: List[Job], resume: str) -> List[Dict[str, Any]]:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = PromptTemplate.from_template("""
You are a career-matching assistant. Compare this résumé to the job posting.

Return ONLY valid JSON with keys:
- match_score (0-100, integer)
- overlaps (list of bullet points)
- gaps (list of bullet points)
- rationale (string, 1–2 sentences)
- remote_eligible (true/false)

Résumé:
{resume}

Job (Company: {company} | Title: {title} | Location: {location}):
{job}
""")

    chain = prompt | llm  # RunnableSequence replaces LLMChain

    results = []
    for job in jobs:
        try:
            output = chain.invoke({
                "resume": resume,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "job": job.description
            })

            # With ChatOpenAI, output is a ChatMessage — get the text
            text = output.content if hasattr(output, "content") else str(output)

            # --- new step: clean markdown fences ---
            text = text.strip()
            if text.startswith("```"):
                # remove leading/trailing triple backticks & optional "json"
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].strip()
                # also remove trailing ``` if still present
                if text.endswith("```"):
                    text = text[:-3].strip()

            try:
                parsed = json.loads(text)
            except Exception as e:
                print(f"[ERROR] JSON parse failed for {job.title} @ {job.company}: {e}")
                print("Raw output:\n", text)
                continue  # skip this job

            results.append({
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "url": job.url,
                "match_score": parsed.get("match_score", 0),
                "overlaps": parsed.get("overlaps", []),
                "gaps": parsed.get("gaps", []),
                "rationale": parsed.get("rationale", ""),
                "remote_eligible": parsed.get("remote_eligible", False),
            })
        except Exception as e:
            print(f"[ERROR] LLM failed for {job.title} @ {job.company}: {e}")

    return results


# -------------------------
# Save results
# -------------------------
def save_results(rows: List[Dict[str, Any]]):
    os.makedirs("output", exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv("output/matches.csv", index=False)

    with open("output/matches.md", "w", encoding="utf-8") as f:
        f.write(make_markdown(rows))


def make_markdown(rows: List[Dict[str, Any]]) -> str:
    lines = ["# Daily Matches", ""]
    for r in sorted(rows, key=lambda x: x["match_score"], reverse=True)[:20]:
        lines.append(f"## {r['title']} — {r['company']} ({r.get('location') or 'N/A'})")
        lines.append(f"- **Match Score:** {r['match_score']}")
        lines.append(f"- **Remote Eligible:** {r.get('remote_eligible', False)}")
        lines.append(f"- **Link:** {r['url']}")
        lines.append(f"- **Rationale:** {r['rationale']}")
        lines.append("")
    return "\n".join(lines)


# -------------------------
# Email digest
# -------------------------
from email.utils import formataddr

def send_email_digest(rows: List[Dict[str, Any]]):
    top = sorted(rows, key=lambda x: x["match_score"], reverse=True)[:30]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Daily EdTech Data Science Matches"
    sender_email = os.getenv("EMAIL_FROM")  # should be plain email only
    recipient_email = os.getenv("EMAIL_TO")

    msg["From"] = formataddr(("Mevo Plus User", sender_email))
    msg["To"] = recipient_email

    html_items = "".join([
        f"<li><b>{r['title']}</b> — {r['company']} ({r.get('location') or 'N/A'}) "
        f"- Score {r['match_score']} - Remote: {r.get('remote_eligible', False)} "
        f"- <a href='{r['url']}'>Apply</a></li>"
        for r in top
    ])
    html = f"<h2>Top Matches</h2><ul>{html_items}</ul>"

    text = "Top EdTech Matches:\n" + "\n".join([
        f"- {r['title']} — {r['company']} [{r['match_score']}] Remote: {r.get('remote_eligible', False)} {r['url']}"
        for r in top
    ])

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())


# -------------------------
# Orchestrator
# -------------------------
def main():
    import yaml
    with open("boards.yaml", "r") as f:
        boards = yaml.safe_load(f)["companies"]

    resume = load_resume()
    all_jobs: List[Job] = []

    for b in boards:
        name, typ = b["name"], b["type"]
        org = b.get("org", "")
        if typ == "greenhouse":
            all_jobs.extend(scrape_greenhouse(org, name))
        elif typ == "lever":
            all_jobs.extend(scrape_lever(org, name))
        elif typ == "custom":
            all_jobs.extend(scrape_workday(org, name))
        elif typ == "html":
            all_jobs.extend(scrape_html(b.get("url", ""), name, org))

    filtered = [j for j in all_jobs if baseline_title_filter(j)]
    print(f"[INFO] {len(filtered)} jobs passed baseline filter out of {len(all_jobs)}")

    rows = rank_jobs_with_llm(filtered, resume)
    print("LLM rows:", rows)
    # OR safer fallback (recommended):
    #if not rows:
     #   print("[WARN] Falling back to baseline filtered jobs")
      #  rows = filtered
    save_results(rows)

    if os.getenv("EMAIL_FROM") and os.getenv("EMAIL_TO"):
        send_email_digest(rows)


if __name__ == "__main__":
    main()
