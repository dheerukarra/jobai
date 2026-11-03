# ApplyForge Personal: Sources and Apply Feasibility

Date: 2026-10-22. Companion to `00-product-brief-v2.md`.
Labels: **FACT** = fetched this session (URL given). **ESTIMATE** = my judgement. **UNVERIFIED** = from memory/prior knowledge, not re-checked today; verify before building.
Context: the owner wants hybrid apply: "it should do it or else then it should go with assisted apply".

Headline findings:
1. Greenhouse and Lever **read** APIs are public, free, keyless. Their **apply** POST endpoints need a key owned by the hiring company, so they are NOT usable for third-party auto-apply. Auto-apply for them means driving the public hosted form in a browser.
2. Best yield per effort: ATS public boards over a curated company list, plus 3-4 free aggregators. LinkedIn/Indeed scraping is a supplement, not the base.
3. Realistic auto-submit share is small (ESTIMATE 15-30% of discovered jobs). The assisted queue is the main product path. Design for it first.

---------------------------------------------------------------------
## PART A: SOURCES
---------------------------------------------------------------------

### A1. Company ATS public boards (highest quality, no ToS fight)

These expose structured JSON for postings that companies publish publicly. Reading is the intended use.

| ATS | List endpoint | Detail | Auth | Notes |
|---|---|---|---|---|
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | `/jobs/{id}?questions=true` returns form fields (questions, location_questions, compliance, demographic_questions) | None for GET | FACT (docs.greenhouse.io/job-board.html, 2026-10-22). Rate limit not documented there. Be polite (1-2 req/s per host). Also `?pay_transparency=true`. `/offices`, `/departments` exist. |
| Lever | `GET https://api.lever.co/v0/postings/{site}?mode=json&skip=0&limit=100` | `/postings/{site}/{id}` | None for GET | FACT (github.com/lever/postings-api). EU tenants: `api.eu.lever.co`. Apply POST needs `?key=` from company Super Admin; limit 2 POST/s. |
| Ashby | `GET https://api.ashbyhq.com/posting-api/job-board/{boardName}?includeCompensation=true` | all in list; has `applyUrl`, `isListed` | None shown | FACT (developers.ashbyhq.com/docs/public-job-posting-api). No public apply endpoint documented. Hosted board: `jobs.ashbyhq.com/{boardName}`. |
| Workable | `GET https://apply.workable.com/api/v1/widget/accounts/{subdomain}` (widget JSON) ; v3 `POST https://apply.workable.com/api/v3/accounts/{sub}/jobs` (body `{"query":"","location":[],...}`) used by the public careers page | `GET /api/v2/accounts/{sub}/jobs/{shortcode}` | None | UNVERIFIED. The v3 POST is the careers-page front-end API (undocumented, may change). Official partner API needs a token. |
| SmartRecruiters | `GET https://api.smartrecruiters.com/v1/companies/{companyId}/postings?limit=100&offset=0` | `/postings/{id}` | None for public postings | UNVERIFIED but long-standing public "Posting API". Detail JSON includes `applyUrl`. |
| Recruitee | `GET https://{company}.recruitee.com/api/offers/` | `/api/offers/{slug}` | None | UNVERIFIED. Returns JSON with descriptions, locations. |
| BambooHR | `GET https://{company}.bamboohr.com/careers/list` (JSON, header `Accept: application/json`) | `/careers/{id}/detail` | None | UNVERIFIED. Undocumented but widely used. |
| Personio | `GET https://{company}.jobs.personio.de/xml` (or `.com/xml`) | XML feed contains full descriptions | None | UNVERIFIED. XML feed is the officially provided feed. |
| Teamtailor | `https://{company}.teamtailor.com/jobs.rss` (RSS) ; official API needs a customer token | RSS item has link | RSS none | UNVERIFIED. |
| JazzHR | `https://{company}.applytojob.com/apply` HTML list; JSON feed via `https://app.jazz.co/feeds/export/jobs/{id}` only for owners | HTML scrape | none for HTML | UNVERIFIED. Scrape HTML; parse schema.org JobPosting JSON-LD on detail pages. |
| Workday | `POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` body `{"appliedFacets":{},"limit":20,"offset":0,"searchText":""}` | `GET .../wday/cxs/{tenant}/{site}/job/{externalPath}` | None | UNVERIFIED but stable for years; this is what the public job site's front end calls. Limit page size to 20; paginate by offset. `N` varies (1,3,5,...). Slow-ish, 1 req/s fine. |
| iCIMS | No public list API. Career portals `careers-{company}.icims.com/jobs/search?ss=1&in_iframe=1`; scrape HTML, or parse JSON-LD on `/jobs/{id}/job` | HTML | none | UNVERIFIED. Many iCIMS sites sit behind Cloudflare/Akamai; yield per effort is low. |
| Taleo (Oracle) | No clean public API. Career section `https://{co}.taleo.net/careersection/{x}/jobsearch.ftl` is HTML+JS, session-based | scrape | none | UNVERIFIED. Skip in v1. |
| Also worth adding | Oracle Recruiting Cloud (`/hcmRestApi/resources/latest/recruitingCEJobRequisitions`), SuccessFactors (HTML), Rippling (`ats.rippling.com/{co}/jobs`), Breezy (`{co}.breezy.hr/json`), Pinpoint (`{co}.pinpointhq.com/postings.json`), Gem (`api.gem.com/job_board/v0/{co}/job_posts/`), Join.com | | none | UNVERIFIED. |

Generic fallback: most job detail pages embed schema.org `JobPosting` JSON-LD. One JSON-LD extractor covers many ATSs plus company sites.

ToS/rate notes (ESTIMATE): these feeds exist to be consumed (Google for Jobs indexes them). Consumption by a personal tool at low rate is low risk. Cache ETag/Last-Modified, poll each board at most 2-4x/day, stagger requests, send an honest User-Agent with a contact address.

### A2. Finding company slugs at scale

Goal: a `companies` table of (ats, slug, name, last_seen, job_count).

1. **Seed list from the owner**: target companies in config (best quality; start here).
2. **Slug probing from company names**: take a list of company names (YC directory, Crunchbase-like open lists, Wikipedia lists, Fortune/Inc lists, the owner's LinkedIn follow list exported manually), generate candidates (`acme`, `acme-inc`, `acmehq`, `getacme`), and probe `boards-api.greenhouse.io/v1/boards/{slug}`, `api.lever.co/v0/postings/{slug}`, `api.ashbyhq.com/posting-api/job-board/{slug}`. A 200 means valid board, 404 means no. Cheap and unauthenticated. ESTIMATE: 10-20% hit rate on tech-company names.
3. **Search-engine discovery**: `site:boards.greenhouse.io "software engineer"`, `site:jobs.lever.co`, `site:jobs.ashbyhq.com`, `site:apply.workable.com`, `site:*.myworkdayjobs.com`, `site:jobs.smartrecruiters.com`. Do it by hand, or via a SERP API (SerpApi free tier ~100/month, UNVERIFIED), or Bing/Brave Search API free tiers (UNVERIFIED). Google itself blocks automated scraping; avoid.
4. **Common Crawl**: the CC index API (`index.commoncrawl.org`, query `url=boards.greenhouse.io/*` with `matchType=prefix` or `jobs.lever.co/*`) lists every captured URL. Extract the first path segment as slug. One-time, free, yields thousands of slugs per ATS. Re-run quarterly. UNVERIFIED on exact counts; method is standard.
5. **Sitemaps**: ATS hosts publish sitemaps for some tenants (e.g. `https://jobs.lever.co/{slug}` pages are linked; `https://boards.greenhouse.io/sitemap.xml` UNVERIFIED). Cheaper to rely on Common Crawl.
6. **Public GitHub lists**: many repos hold curated lists of Greenhouse/Lever/Ashby board slugs and "awesome remote companies" (search GitHub for `greenhouse board tokens`). UNVERIFIED; use as seeds, then validate by probing.
7. **Passive harvesting**: every aggregator result links to an apply URL. Parse ATS+slug out of URLs from Adzuna/JSearch/Jooble/LinkedIn results and add to `companies`. This snowballs and is the highest-leverage trick.
8. **Prune**: drop boards with 0 jobs for 60 days; weight polling by relevance hit rate.

### A3. Aggregator APIs (free tiers)

| Source | Endpoint / access | Free tier / limits | Terms notes |
|---|---|---|---|
| Adzuna | `GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}?app_id=&app_key=&what=&where=` | FACT: endpoint pattern and app_id/app_key required (developer.adzuna.com/overview). Free-tier numbers not on that page; UNVERIFIED memory says about 250 calls/day per key, 25/min. | Per ToS, display attribution/links back; results are redirect links via adzuna.com. Personal use fine. Covers US, UK, CA, AU, DE, IN, etc. |
| JSearch (OpenWeb Ninja / RapidAPI) | `GET https://jsearch.p.rapidapi.com/search?query=` (RapidAPI) ; now also via openwebninja.com | Pricing page not retrievable today. UNVERIFIED memory: free plan ~200 requests/month, paid from ~$25. Data comes from Google for Jobs (which includes LinkedIn/Indeed/Glassdoor listings). | Best "single call covers many boards" option; apply links to original posting. Budget the monthly cap; use for gap-fill only. |
| USAJobs | `GET https://data.usajobs.gov/api/search` with headers `Authorization-Key` and `User-Agent: <your email>`; key from developer.usajobs.gov | Page lacked specifics (FACT: docs at developer.usajobs.gov/guides/authentication and /guides/rate-limiting). Free; key by email. | US federal jobs only; US-citizenship requirements are common, so filter by the owner's work authorization. Applies happen on usajobs.gov (login, assisted only). |
| The Muse | `GET https://www.themuse.com/api/public/jobs?page=0&category=...` | UNVERIFIED: 500 req/hr unauthenticated, higher with key. | Free for use with attribution. Small, US-centric, big-brand corporate. |
| Remotive | `GET https://remotive.com/api/remote-jobs?category=&search=&limit=` | FACT (github.com/remotive-com/remote-jobs-api): fetch at most ~4x/day; over 2 req/min gets blocked; 24h delayed. | FACT: must link back to the Remotive URL and name Remotive as source; do not resubmit their jobs to LinkedIn, Google Jobs, Jooble etc. Personal tool is fine. |
| RemoteOK | `GET https://remoteok.com/api` (JSON; first element is legal notice) | UNVERIFIED: no key; send a UA. | UNVERIFIED: their notice requires linking back and credit. |
| We Work Remotely | RSS: `https://weworkremotely.com/categories/remote-programming-jobs.rss` and `/remote-jobs.rss` | UNVERIFIED: no key. | RSS intended for consumption; link back. |
| Arbeitnow | `GET https://www.arbeitnow.com/api/job-board-api` | FACT: that URL is the documented endpoint (arbeitnow.com/api). Auth/limits not on page. UNVERIFIED: free, no key. | Europe/Germany heavy, visa-sponsorship flag exists. Check terms at arbeitnow.com/terms. |
| Jooble | `POST https://jooble.org/api/{API_KEY}` body `{"keywords":"","location":""}` | UNVERIFIED: free key by request form; limits not published. | Partner-style ToS; fine for personal use. |
| Himalayas | `GET https://himalayas.app/jobs/api` (JSON; params limit/offset) | UNVERIFIED: free, rate-limited (about 20 per call, reasonable cadence); ToS asks for attribution. | Remote jobs, good metadata (salary, timezone). |
| HN "Who is hiring?" | Algolia `GET https://hn.algolia.com/api/v1/search?query=Ask HN: Who is hiring&tags=story,author_whoishiring` then Firebase `https://hacker-news.firebaseio.com/v0/item/{id}.json` for comments | UNVERIFIED: no key; Algolia ~10k req/hr. | Monthly thread (first of month). Free text, needs LLM parsing; contains direct emails (assisted: draft email). High quality for startups. |
| SerpApi Google Jobs | `GET https://serpapi.com/search?engine=google_jobs&q=` | UNVERIFIED: free tier ~100 searches/month. | Paid scrape-proxy for Google. Good for gap-fill; low volume. |
| Careerjet | `GET https://public.api.careerjet.org/search?...` (affiliate id) | UNVERIFIED: free, needs affiliate key and user-IP/user-agent params. | Affiliate ToS: must send end-user IP/UA; for a single-user tool use your own IP. |
| Others to consider | Jobicy API, Findwork.dev (free key), Reed (UK, free key), Indeed Publisher (closed), Remote.co, Working Nomads JSON, Greenhouse/Lever aggregators like `jobs.ashbyhq.com` | | UNVERIFIED |

### A4. Open-source scrapers for LinkedIn / Indeed / Glassdoor / ZipRecruiter

**Plain statement:** scraping LinkedIn, Indeed, Glassdoor and ZipRecruiter violates their Terms of Service (all four prohibit automated access). Logged-out scraping of publicly visible pages involves no account of the owner, so there is no account to ban or suspend; the realistic consequence is IP blocking/CAPTCHA walls, and (ESTIMATE, low probability for a single personal user) a cease-and-desist is unlikely at this scale. Do not log in with the owner's account for any scraping.

| Tool | What it does | Status (checked today) |
|---|---|---|
| **JobSpy / python-jobspy** (`speedyapply/JobSpy`, PyPI `python-jobspy`) | One call scrapes LinkedIn, Indeed, Glassdoor, ZipRecruiter, plus Bayt, Naukri, BDJobs, HelloWork; returns a pandas DataFrame. Logged-out HTTP scraping (no browser). `proxies` param round-robins; `results_wanted`, `hours_old`, `linkedin_fetch_description` options. | FACT (github.com/speedyapply/JobSpy, 2026-10-22): about 4.5k stars, 895 forks, 388 commits, 13 open issues. Last-commit date and releases not visible on page, so maintenance recency is UNVERIFIED; check Insights/Commits before depending on it. FACT per README: LinkedIn returns 429 on bursts, clears in about a minute; Indeed is the best-working scraper with no rate limiting noted; Glassdoor limits above ~2 req/s; searches cap near 1,000 jobs; Google Jobs scraping currently unavailable; SOCKS needs `requests[socks]`. |
| `JobSpy` forks/wrappers | Several MCP and API wrappers around JobSpy | UNVERIFIED; prefer the upstream lib and pin a version. |
| `linkedin-jobs-scraper` (npm/py, `spinlud`) | Headless browser LinkedIn public search | UNVERIFIED; browser-based, heavier, breaks on markup changes. |
| LinkedIn guest endpoints | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=&location=&start=0` and `/jobs-guest/jobs/api/jobPosting/{id}` return HTML fragments without login | UNVERIFIED: this is what JobSpy uses. Pagination to about start=1000; heavy 429/999 beyond a few hundred requests per IP-hour (ESTIMATE). |
| Apify actors / hosted scrapers | Paid per-run scrapers for LinkedIn/Indeed/Glassdoor | UNVERIFIED; costs money (brief wants near-zero). Fallback only. |

Behaviour notes (ESTIMATE from general experience, label accordingly):
- **Indeed**: highest yield, tolerant at low rate; Cloudflare challenge appears on datacenter IPs more often than residential.
- **LinkedIn**: guest listing works, throttles around 10 pages per IP burst; descriptions need one extra request per job (do that only for jobs that pass the title filter).
- **Glassdoor**: location ID quirks, frequent breakage; low priority.
- **ZipRecruiter**: tends to block datacenter IPs aggressively; low priority.
- If hosted on a cloud free tier, datacenter IPs get blocked sooner than home IPs. This matters for the hosting decision: running discovery from a small home/Raspberry-type box or a residential IP is more reliable than from a cloud VM.

### A5. Reducing IP blocking cheaply (no evasion tricks)

1. Be a low-volume reader: 1-2 searches per site per run, 2-4 runs/day, `hours_old=24` so each run is a small delta.
2. Random jitter 3-10 s between requests; one request at a time per host.
3. Cache aggressively: store seen `job_url`; never re-fetch detail pages; use ETag where offered.
4. Fetch descriptions lazily, only after the title/company/location filter passes.
5. Back off exponentially on 429/403 and trip a per-source circuit breaker for 6-24 h; log it on the dashboard rather than hammering.
6. Prefer sources that don't need scraping first (ATS APIs, aggregators); scrape boards only to fill gaps.
7. Cheap IP diversity: run from the owner's home IP (a small always-on device) plus the cloud host; optionally a rotating-proxy free list is unreliable (ESTIMATE: mostly dead/poisoned), so budget at most a few dollars per month for a single residential/ISP proxy if needed. A VPN exit is a one-line fallback.
8. Make a source-health table: last success, block rate, yield; auto-disable sources that fail 3 runs.

### A6. Recommended source stack (ranked by yield per effort)

| Rank | Source | Effort | Why |
|---|---|---|---|
| 1 | Greenhouse + Lever + Ashby boards over a curated 300-2000 company list | Low | Free, structured, full descriptions, form questions exposed (Greenhouse), stable. Best apply feasibility too. |
| 2 | Slug harvesting from other sources + Common Crawl seeding | Low-Med | Grows the list 10x for free. |
| 3 | Workable, SmartRecruiters, Recruitee, Personio, Ashby extras | Low | Same adapter pattern, a few lines each. |
| 4 | Adzuna (US/UK/CA etc.) | Low | Large volume, free key. |
| 5 | JobSpy (Indeed first, then LinkedIn guest) | Med | Biggest raw volume but fragile; cap and cache. |
| 6 | Remote feeds: Remotive, RemoteOK, WWR, Himalayas, Arbeitnow | Low | Small, clean, only if owner wants remote. |
| 7 | HN Who is hiring (monthly) | Low | High quality startups, email-apply. |
| 8 | JSearch/SerpApi (quota-limited) | Low | Gap filler on a monthly budget. |
| 9 | Workday CXS for a hand-picked list of big employers | Med | Great volume per tenant but apply is assisted-only. |
| 10 | USAJobs, The Muse, Jooble, Careerjet | Low | Situational. |

### A7. Dedupe strategy across sources

Three levels:
1. **Exact**: `canonical_url` (strip query/utm, lowercase host, strip trailing slash, resolve aggregator redirects to the final ATS URL once) and `(ats, board_slug, job_id)`. Same posting on LinkedIn and on the Greenhouse board collapses when the apply URL resolves to the ATS URL.
2. **Fingerprint**: `sha1(norm(company) | norm(title) | norm(city/remote flag) )` with normalisation (lowercase, remove "senior/sr.", punctuation, level suffixes kept separate). Catches the same role posted via different aggregators.
3. **Near-duplicate**: embedding or trigram similarity on title + first 500 chars of description, same company, posted within 45 days, similarity above ~0.92 (ESTIMATE threshold; tune on real data). Merge into one `job` row with multiple `source_urls`; keep the **ATS-native URL as the primary apply target** (best auto-apply route), then aggregator URL.
4. **Application-level guard** (brief requirement): unique constraint on `(company_norm, title_norm, req_id|location)` for applications, plus per-company cooldown (e.g. no second application to the same company within 30 days unless the owner overrides), and a global "already applied" check by company+title before any submit.
5. Reposts: if the fingerprint matches an applied job and age < 90 days, mark `repost_skip`.

---------------------------------------------------------------------
## PART B: AUTO-APPLY FEASIBILITY PER ATS
---------------------------------------------------------------------

Method note: public GET data is easy; **submission** is what differs. For each ATS: is there a public POST usable without the company's secrets, or only the browser form?

### B1. Summary table

| Target | Programmatic route | CAPTCHA / bot layer | Account needed | Class | Auto-submit success (ESTIMATE, when route decision says go) |
|---|---|---|---|---|---|
| Greenhouse (hosted `boards.greenhouse.io` / `job-boards.greenhouse.io`) | Browser form fill. The documented POST needs the company's Basic-auth API key (FACT docs.greenhouse.io/job-board.html), so unavailable to us. | Many boards show reCAPTCHA (invisible/Enterprise) on submit; others none. UNVERIFIED which proportion. Greenhouse also has emailed security-code verification on some boards (UNVERIFIED, introduced around 2025). | No | AUTO-LIKELY for boards without captcha/verification code; else ASSISTED | 60-80% on eligible boards; overall about 35-50% of Greenhouse jobs (ESTIMATE) |
| Lever (hosted `jobs.lever.co/{site}/{id}/apply`) | Browser form fill. API POST needs the company key (FACT github.com/lever/postings-api). | hCaptcha shown on many Lever application forms (UNVERIFIED but widely reported). | No | AUTO-LIKELY only where no captcha appears; mostly ASSISTED | 40-60% of eligible; overall about 20-35% (ESTIMATE) |
| Ashby (`jobs.ashbyhq.com/{board}/{id}/application`) | Browser form fill. GraphQL front-end API exists but undocumented. | Invisible reCAPTCHA scoring; spam-score rejections are reported (UNVERIFIED) | No | ASSISTED-ONLY by default; AUTO-LIKELY experimental | 30-50% overall (ESTIMATE); failure can be silent (marked spam) |
| Workable (`apply.workable.com/{co}/j/{code}`) | Browser form fill | reCAPTCHA/Cloudflare shown on some (UNVERIFIED); forms are React with custom widgets | No (guest apply) | ASSISTED-ONLY (v1), maybe AUTO later | 25-40% (ESTIMATE) |
| SmartRecruiters (`jobs.smartrecruiters.com/{co}/{id}`; apply on `.../apply`) | Browser; multi-step with account-like "Oneclick" prompts | reCAPTCHA/bot checks and email verification common (UNVERIFIED) | Often optional, email confirm | ASSISTED-ONLY | 15-30% (ESTIMATE) |
| Workday | Browser only; multi-page wizard | Cloudflare/Akamai on some tenants; per-tenant account creation + email verification | **Yes, per-tenant account** | AVOID for auto (secrets rule: no ATS passwords in DB) -> ASSISTED | <10% (ESTIMATE) |
| iCIMS | Browser; account/profile creation commonly required; iframes | Often Akamai/Cloudflare + reCAPTCHA | Usually yes | AVOID auto -> ASSISTED | <10% (ESTIMATE) |
| Taleo / SuccessFactors / Oracle | Browser; legacy multi-step; account required | Varies | Yes | AVOID -> ASSISTED | <5% (ESTIMATE) |
| LinkedIn Easy Apply | Browser, only in the logged-in session | Heavy behavioural detection; account restrictions are the known consequence | Owner's own login | AVOID (and out of bounds by brief: no owner account used by bots). Use only as discovery; apply link goes to assisted queue. | n/a |
| Indeed Apply | Browser, logged-in; Indeed also uses its own hosted flow | Cloudflare + login + phone/email verification | Owner login | AVOID -> ASSISTED (open the original apply link) | n/a |
| Recruitee / Personio / BambooHR / Teamtailor / JazzHR | Browser; simple forms | Mostly light or none; some reCAPTCHA | No | AUTO-LIKELY (experimental, after Greenhouse is proven) | 40-60% (ESTIMATE) |
| Email-apply (HN, small companies) | Send email with resume from owner's own mailbox/SMTP | None | No | AUTO-LIKELY with owner-approved template | high deliverability, response rate low |

Class definitions: **AUTO-LIKELY** = attempt automatically when the route decision passes all gates; **ASSISTED-ONLY** = never auto-submit in v1, always queue; **AVOID** = do not attempt automation at all (account, secrets or ToS-heavy).

### B2. Per-ATS detail

**Greenhouse**
- Public data: FACT `GET boards-api.greenhouse.io/v1/boards/{token}/jobs/{id}?questions=true` returns the exact form schema (name, email, phone, resume, cover letter, custom questions with types and options, location questions, compliance/EEO/demographic blocks). This is a huge win: the LLM question mapper can run on the schema **before** opening a browser, so the route decision is made at triage time with no page load.
- Submission: FACT docs state POST is HTTP Basic with the company's API key, multipart or JSON, resume as file/URL/text, Greenhouse does not validate required fields for you. We cannot use it without the employer's key. Do NOT try to obtain or guess keys. Use the hosted form via Playwright.
- Typical fields: first/last name, email, phone, resume (file input), cover letter, LinkedIn URL, website, "How did you hear", work-authorization/sponsorship (select), 0-6 custom text/select/multi-select, EEO (gender, race, veteran, disability: optional "decline to answer").
- Resume upload: `<input type=file>` -> `setInputFiles`; some boards use an "attach" button plus a hidden input; parse of resume sometimes autofills fields, so re-set values after upload.
- Bot protection: FACT docs mention only generic "built-in spam protection" for the embedded form. UNVERIFIED: reCAPTCHA Enterprise on many boards, plus a security-code email step on some. Detection rule: presence of `iframe[src*="recaptcha"]`, `.g-recaptcha`, "security code" input after submit.
- Email verification: if a code field appears post-submit -> mark `needs_human` (could read from owner's inbox only if the owner explicitly enables it; default no).

**Lever**
- FACT: apply endpoint needs the company key; 2 POST/s limit; the doc itself recommends custom forms add captchas. The hosted form `jobs.lever.co/{site}/{id}/apply` has fields: full name (single field), email, phone, current company, URLs (LinkedIn, GitHub, portfolio), resume, additional info, custom questions (cards), EEO block.
- hCaptcha frequently present (UNVERIFIED). If challenge iframe detected -> assisted. No bypass.
- Lever's form is simple and stable DOM (`input[name="name"]`, `input[name="email"]`, `input[name="resume"]`); good for automation when no captcha.

**Ashby**
- FACT: public posting API is read-only; `applyUrl` points to hosted application. Form is a React app; custom fields are typed (text, select, boolean, file). Spam scoring is invisible, so submissions from a datacenter IP with fast fill can be silently flagged (UNVERIFIED). Treat success as unconfirmed; require the confirmation page text ("Thanks for applying") plus a follow-up email check before counting as applied.

**Workable**
- Public job JSON available; application form is a React widget with file upload, questions, "Application submitted" confirmation. Candidates may be asked to create nothing (guest). Cloudflare Turnstile/reCAPTCHA appears on some (UNVERIFIED). Start as assisted; revisit.

**SmartRecruiters**
- Public postings API (UNVERIFIED) gives questions? Not reliably; the apply flow has a multi-step form and sometimes a "smart profile" login prompt. Assisted-only.

**Workday**
- Reading is easy (CXS JSON). Applying requires creating a tenant-specific account (email+password) and email verification; each company is a separate account. Brief rule: no ATS passwords stored in DB -> **assisted**. Optional later: owner-managed password manager session, not in scope. Applications take 15-30 min of structured data entry (education, work history repeated); the assisted "prefilled" value here is to give the owner a ready text block and the resume.
- Open-source Workday-focused bots exist (see B3); they use persistent accounts and often break on tenant customisations.

**iCIMS / Taleo / SuccessFactors**
- Account creation and legacy multi-page forms; frequent iframes and bot managers. Assisted.

**LinkedIn Easy Apply**
- Only works in the owner's logged-in session. Automated Easy Apply is a known ban trigger (UNVERIFIED but widely reported: temporary restrictions then permanent). Brief says no owner account used for automation. Use LinkedIn as a discovery source only; resolve "Apply on company website" links to the ATS (via the job's `applyUrl` in guest HTML when present); Easy Apply-only jobs -> assisted (owner taps and does it).

**Indeed Apply**
- Requires Indeed login; Cloudflare; phone/email verification. Same treatment: discovery only; try to resolve the employer's ATS link; otherwise assisted.

### B3. Open-source auto-apply projects and lessons (checked today)

| Project | Status (FACT unless noted) | What it teaches |
|---|---|---|
| `Pickle-Pixel/ApplyPilot` (README says first published 2026-02-17) | FACT: about 1.7k stars, 628 forks, 36 commits. Six-stage pipeline: discover (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google Jobs, 48 Workday portals), score, tailor resume, cover letter, auto-apply via Claude Code driving Chrome. | Same architecture as ours. Its README integrates a paid captcha-solving key; we explicitly do not (brief: CAPTCHA = assisted). Notes that blocked applications simply fail; good reminder to record failure reasons and fall back. |
| `ibarrajo/ApplyPilot` | Search result (not opened): Claude Code + Playwright MCP, multi-LLM fallback, AGPL-3.0. Stars UNVERIFIED. | AGPL licence: do not copy code into a closed tool; read for ideas only. |
| `AIHawk-FOSS/Auto_Jobs_Applier_AI_Agent` (formerly feder-cr/Auto_Jobs_Applier_AIHawk) | FACT: the page I fetched shows about 32k stars, 4.7k forks, 418 commits, but its README text described a different "Dot" agent product (alpha), so the repo appears to have been repurposed. Treat the identity and current focus as UNVERIFIED and check the repo before using. | Historically (UNVERIFIED) a LinkedIn Easy Apply bot; the 30k+ stars show demand, and its issue history is widely reported to include account restrictions for users. Do not model on LinkedIn Easy Apply. |
| `proficientlyjobs/proficiently-claude-skills` | Search result: about 278 stars per an undated listing (UNVERIFIED), MIT, submits to Greenhouse, Lever, Workday via a Claude Code plugin. | Confirms the three ATSs people target most; MIT so adaptable. |
| `maazkhanxo/jobeasyapply-linkedin-auto-apply` | Search result: MV3 Chrome extension, Greenhouse + Lever + LinkedIn, handles custom dropdowns (UNVERIFIED stars). | Custom dropdowns/typeahead (React-select) are the main fill failure mode; build robust select helpers. |
| Chrome extensions (Simplify, Jobscan-style, Job Copilot) | Closed source; commercial | Show the **assisted** pattern at scale: autofill at the user's own browser with the user pressing Submit. That is the most reliable approach and mirrors our assisted queue. |

Lessons across these (ESTIMATE/synthesis): (1) form-fill is easy, answer correctness is the real risk; (2) required-field and dropdown matching dominate failures; (3) per-ATS adapters beat a fully generic agent for reliability and cost; generic LLM-driven browser agents are 5-20x costlier per application (ESTIMATE) and slower; (4) success must be verified by confirmation page/email, not by "clicked submit".

---------------------------------------------------------------------
## PART C: ROUTE DECISION ALGORITHM
---------------------------------------------------------------------

Runs per job after scoring, before any browser launch where possible. Output: `AUTO | ASSISTED | SKIP` plus `reasons[]`. Everything defaults to ASSISTED on any doubt.

```
route(job):
  0. GLOBAL GATES -> SKIP/ASSISTED
     - kill switch on, dry-run on (dry-run: do all steps, never click submit, log "would submit")
     - already applied (dedupe) -> SKIP
     - daily/company/ATS caps reached -> defer (retry tomorrow) or ASSISTED
     - fit score < threshold (e.g. 0.6) -> SKIP; entity-diff of tailored resume fails -> BLOCK (back to tailoring or ASSISTED)

  1. DETECT ATS (cheap, no page load)
     host/path patterns: boards.greenhouse.io|job-boards.greenhouse.io|?gh_jid=, jobs.lever.co,
     jobs.ashbyhq.com, apply.workable.com, jobs.smartrecruiters.com, *.myworkdayjobs.com,
     *.icims.com, *.taleo.net, *.recruitee.com, *.bamboohr.com, *.jobs.personio.*, *.teamtailor.com,
     linkedin.com/jobs, indeed.com/viewjob.
     Aggregator link? follow redirects once (HEAD/GET, 5 hops max) to the final apply URL.
     Company site with embed? Look for ATS markers in DOM later (iframe src, script src, `gh_jid`).
     unknown ATS -> ASSISTED.

  2. CLASS POLICY (table B1)
     ASSISTED-ONLY / AVOID class -> ASSISTED immediately (store prefilled kit).
     Per-ATS "live submit enabled" flag must be true (brief: owner enables per ATS) else dry-run.

  3. FORM SCHEMA
     Greenhouse: fetch ?questions=true JSON (no browser).
     Others: open the apply page headless (low-rate), extract fields from DOM (labels, input types,
     options, required flags). Cache schema per (ats, company, job).

  4. WALL DETECTION (stop at first hit -> ASSISTED, reason recorded; never attempt to bypass)
     - login/account: password field, "Create account", "Sign in to apply", Workday/iCIMS paths
     - CAPTCHA/bot: iframes/scripts for recaptcha, hcaptcha, turnstile, arkose; Cloudflare/Akamai
       interstitial titles ("Just a moment"), HTTP 403/429 on the form page
     - email verification promised ("we sent you a code") -> if only discoverable post-submit,
       mark attempt `needs_human` and send assisted notification
     - file types: resume field accepts only formats we can provide (PDF/DOCX)
     - multi-page wizard longer than N steps (e.g. 3) -> ASSISTED
     - "upload only, no parsing", video/assessment/coding-test questions -> ASSISTED

  5. QUESTION MAPPING (LLM, Haiku, JSON-schema output)
     Input: field label/help text/type/options + answers bank + profile facts + job context.
     Output per field: {value, source: "bank|profile|resume|generated", confidence 0-1, matched_key}.
     Rules:
       - Deterministic first: regex/keyword map for name, email, phone, links, location, pronouns.
       - Bank-only fields (work auth, sponsorship, salary, relocation, notice period, EEO, clearance,
         criminal record, disability, veteran): value MUST come from the bank by exact key; if no
         key -> unknown. EEO default per owner's bank (often "decline to answer").
       - Select/radio: output must equal one of the option strings (validate); else unknown.
       - Free-text "why us"/essay: generated from resume + job, allowed only if the owner's
         policy permits; run entity-diff (no invented employers/skills/numbers); length limits;
         if policy = manual-essays -> ASSISTED.
       - Legal attestations/consent checkboxes (terms, "I certify"): owner pre-approves a fixed list;
         anything novel -> unknown.
     Thresholds (ESTIMATE starting values, tune on logs):
       - every required field: confidence >= 0.85 for generated, bank/profile exact match = 1.0
       - any unknown required field -> ASSISTED
       - >= 1 optional field below 0.6 -> leave blank if optional, else treat as required unknown
       - total fields <= 25 and custom questions <= 8, else ASSISTED

  6. PRE-SUBMIT CHECKS
     - fill via Playwright with human-like but ordinary pacing, per-host rate limit, one job at a time
     - verify DOM values equal intended values (read back), no validation errors visible
     - screenshot + HTML snapshot stored with the attempt
     - if dry-run: stop here, route = "AUTO (dry)"

  7. SUBMIT + VERIFY
     click submit; success only if confirmation text/URL pattern matches that ATS adapter
     (e.g. "Application submitted", /confirmation) OR confirmation email later arrives (tracker).
     If a captcha/verification appears at this point -> do not proceed, move to ASSISTED with the
     already-filled kit. Timeout 90 s per attempt, 1 retry for transient errors only.
     Record: attempt id, route, reasons, confidence summary, artifacts.

  8. FALLBACK TO ASSISTED (always available)
     Assisted card contains: job title/company/link (ATS-native URL), tailored resume PDF, cover
     note, a copy-ready answers table keyed to the form's questions (from step 5, flagged unknowns
     highlighted), the reason it was not automated, and a push notification (ntfy/Telegram) with
     a one-tap link. Owner marks Done / Skipped; outcome feeds the tracker.
```

Learning loop (cheap): log every wall/failure by (ats, company); after 3 consecutive wall hits for a company, mark that company ASSISTED-ONLY to stop wasted attempts. Track ATS-level success rate in the dashboard and auto-disable AUTO for an ATS if success < 50% over the last 20 attempts.

---------------------------------------------------------------------
## PART D: Risk summary (no moralising)

| Area | Risk | Mitigation |
|---|---|---|
| ATS public GET APIs | Very low. Intended for consumption. | Polite rate, cache, UA with contact. |
| Aggregator APIs | Low; attribution and quota terms (Remotive explicitly requires backlink and caps polling) | Respect each limit; store source and link. |
| JobSpy / guest scraping of LinkedIn, Indeed, Glassdoor, ZipRecruiter | Violates those sites' ToS. No owner account involved, so no account ban; likely outcome is IP block/429 or CAPTCHA. Fragile: breakage on markup changes. | Low rate, cache, circuit breaker, home IP if possible, treat as optional source. |
| Browser auto-submit on hosted ATS forms | Company ToS typically bar automated submissions; practical outcome is a silent spam flag or rejection of that application, and in rare cases a blocklist entry at that employer. | Limit to AUTO-LIKELY ATSs, honest data only, caps per company, quality over volume. |
| LinkedIn/Indeed logged-in automation | Highest: owner account restriction. | Excluded by design. |
| Wrong answers (work authorization, salary) | Highest practical harm: wrongful rejection or misrepresentation. | Answers bank only; unknown -> assisted; owner reviews bank. |
| Employer-side duplicate spam | Applying to many roles at one company hurts chances. | Per-company cap, cooldown. |

## Open items for the owner
1. Provide work authorization/sponsorship answer set and EEO preference for the bank.
2. Choose target geography and remote preference (drives Adzuna countries, Arbeitnow, remote feeds).
3. Decide whether the tool may read the owner's inbox for verification codes (default: no).
4. Verify UNVERIFIED items marked above with a 1-hour spike per adapter before committing (first spike order: Greenhouse form fill, Lever form fill, Ashby, Workable).
