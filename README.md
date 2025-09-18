# EdTech Job Agent

Scrapes EdTech company job boards (Greenhouse, Lever, Workday, HTML), compares them to your résumé using LangChain + OpenAI, and emails a daily digest of best matches.

Features:
- Greenhouse & Lever APIs
- Workday (McGraw Hill example implemented)
- HTML scraping (generic + Kahoot! + Nearpod)
- LLM comparison with match score, overlaps, gaps, rationale, remote_eligible
- Smarter researcher handling in baseline_title_filter
- Outputs CSV + Markdown + email digest
- GitHub Actions for daily automation
