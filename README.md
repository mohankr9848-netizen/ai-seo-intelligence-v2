# SEO Intelligence — Complete 9-feature prototype (₹0 software budget)

One Streamlit dashboard with: (1) keyword research and clustering, (2) competitor topic gaps, (3) internal link suggestions, (4) optional PageSpeed API, (5) content strategy and 12-week calendar, (6) schema templates and local validation, (7) GEO heuristic checks, (8) opportunity scoring, and (9) client PDF report.

## Install and run

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
streamlit run app.py
```

## Deploy for controlled testing

1. Create a GitHub repo and upload the **contents** of this folder (app.py at repo root).
2. Visit https://share.streamlit.io and connect the GitHub repository.
3. Select `main` branch, `app.py` as the entrypoint, and deploy.
4. Keep the app access-restricted to trusted testers until security hardening is complete.

## Key accuracy boundaries

- **AI-labeled features are offline heuristic / classical ML implementations**, not a generative AI model. Keyword clustering uses TF-IDF and KMeans; content calendar uses templates. No API key or local LLM is required. This is a complete functional prototype, not a claim of full commercial SEO data parity.
- **Keyword volume, difficulty, competitor rankings, AI citations** are not measured and never fabricated.
- **Competitor gaps** are content-term differences in sampled metadata, not Google ranking gaps.
- **GEO** is a heuristic checklist; it cannot predict inclusion in AI search results.
- **Schema validator** checks JSON structure and a few required fields, not all Schema.org or Google rich-result requirements.
- **PageSpeed** uses Google's API when enabled. Unauthenticated requests may fail; free quotas and API policies may change. The dashboard displays errors instead of inventing results.
- **Sitemap** discovery supports a direct /sitemap.xml only, not recursive sitemap indexes.
- **Crawl** is same-host, robots-aware, bounded to 50 pages, and HTML-focused. JS-rendered content, advanced redirects, complete broken-link validation and multi-sitemap discovery are not covered.
- **PDF** summarizes key audit and strategy outputs, not every data table. CSV exports provide full findings.

## Public SaaS security warning

**Do not launch as an unrestricted public SaaS without further engineering.** A user-controlled URL fetcher is an SSRF risk. The crawler validates public DNS IPs before each request and disables environment proxies, but that does not prevent DNS rebinding between validation and socket connection. You need network egress controls that prevent access to loopback, link-local, private, metadata and other internal addresses, and preferably DNS-to-socket IP pinning. Also add authentication, per-user and per-IP quotas, a job queue, persistent storage, concurrency caps, usage monitoring, privacy and terms policies, and production observability. Streamlit Community Cloud is a free prototype host with resource limitations.

Respect robots.txt, website terms, crawl pacing, and third-party intellectual property. Only audit websites you own or are authorized to audit.
