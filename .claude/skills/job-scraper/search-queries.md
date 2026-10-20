# Search Queries for Job Scraper

<!-- SETUP: Customize these queries based on your skills, target roles, and location -->

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Shipped country-agnostic CLIs include `linkedin-search` and `freehire-search` (both enabled); the four Danish portal skills remain disabled (`enabled: false`) since your target market is Indonesia & Remote (APAC / Global).

Recommended CLI invocations for `/scrape`:
- **`linkedin-search`**:
  - `bun .agents/skills/linkedin-search/cli/src/index.ts search -q "Golang Backend Engineer" -l "Jakarta, Indonesia" --format json`
  - `bun .agents/skills/linkedin-search/cli/src/index.ts search -q "Java Spring Boot Backend" -l "Indonesia" --format json`
  - `bun .agents/skills/linkedin-search/cli/src/index.ts search -q "Backend Engineer AI LLM" -l "Indonesia" --format json`
  - `bun .agents/skills/linkedin-search/cli/src/index.ts search -q "Golang Engineer" -l "Remote" --remote --format json`
- **`freehire-search`**:
  - `bun .agents/skills/freehire-search/cli/src/index.ts search -q "Golang" --remote --format json`
  - `bun .agents/skills/freehire-search/cli/src/index.ts search -q "Spring Boot" --remote --format json`
  - `bun .agents/skills/freehire-search/cli/src/index.ts search -q "MCP" --remote --format json`

The `site:` query templates below are the **WebSearch fallback** — for Indonesian portals without a dedicated CLI, company career pages, or when a CLI fails.

**Language scope:** Queries are written in both **English** (the primary language for tech job postings in Indonesia and globally) and **Indonesian** (per your CLAUDE.md Languages table).

## Search Sites

Primary (Indonesia & Global Remote job boards - scaffold a CLI for any of these with `/add-portal`):
- **linkedin.com/jobs** - LinkedIn job listings (filter: Indonesia, Jakarta, or Remote); also covered by `linkedin-search` CLI
- **freehire.me** - Multi-market tech & remote aggregator; covered by `freehire-search` CLI
- **glints.com** - Glints Indonesia & SEA tech/startup job board
- **id.jobstreet.com** - JobStreet Indonesia (largest general & enterprise job board in Indonesia)
- **kalibrr.com** - Kalibrr Indonesia enterprise & tech job board
- **dealls.com** - Dealls Indonesia startup & tech job board
- **techinasia.com/jobs** - Tech in Asia Jobs (Indonesia & SEA startups)

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for target tech, fintech, and AI companies in Indonesia & APAC

## Query Categories

### Priority 1: Backend & Senior Backend Engineering (Golang / Java Spring Boot)

These match your strongest and most desired career direction (~4+ years building high-traffic, zero-downtime services in Go and Java).

```
site:linkedin.com/jobs ("Backend Engineer" OR "Backend Developer" OR "Senior Backend Engineer") ("Golang" OR "Go" OR "Spring Boot") ("Jakarta" OR "Indonesia" OR "Remote")
site:glints.com ("Backend Engineer" OR "Backend Developer" OR "Software Engineer Backend") ("Golang" OR "Spring Boot") ("Jakarta" OR "Indonesia" OR "Remote")
site:id.jobstreet.com ("Backend Developer" OR "Backend Engineer") ("Golang" OR "Java Spring Boot") Jakarta
site:dealls.com ("Backend Engineer" OR "Backend Developer") ("Golang" OR "Java")
site:kalibrr.com ("Backend Engineer" OR "Software Engineer") ("Golang" OR "Spring Boot") Indonesia
site:id.jobstreet.com ("Pengembang Backend" OR "Programmer Backend") ("Golang" OR "Java") Jakarta
```

### Priority 2: Applied AI / LLM Backend Engineering (Agentic AI, MCP, RAG, Computer Vision)

These match your production experience integrating LLMs, Model Context Protocol (MCP), Qdrant RAG, Facial Recognition (FR), ANPR, and ElevenLabs into enterprise backends.

```
site:linkedin.com/jobs ("AI Engineer" OR "LLM Engineer" OR "AI Backend Engineer" OR "GenAI Engineer") ("Golang" OR "Java" OR "RAG" OR "MCP" OR "Qdrant") ("Indonesia" OR "Remote")
site:glints.com ("AI Engineer" OR "Backend Engineer") ("LLM" OR "RAG" OR "GenAI" OR "Vector") ("Jakarta" OR "Indonesia" OR "Remote")
site:techinasia.com/jobs ("AI Engineer" OR "Backend Engineer") ("Golang" OR "Java" OR "LLM") Indonesia
site:linkedin.com/jobs ("Computer Vision" OR "Face Recognition" OR "RTSP" OR "MQTT") ("Backend" OR "Java" OR "Golang") Indonesia
```

### Priority 3: Full-Stack & Product Engineering (Go / Java + React / TypeScript / Electron)

Adjacent roles leveraging your end-to-end product delivery (`apitester`, `Bestcuci.id`, `Phisio.book.app`) across Go/Java backends and React 19 / TypeScript / Electron frontends.

```
site:linkedin.com/jobs ("Full Stack Engineer" OR "Fullstack Developer" OR "Product Engineer") ("Golang" OR "Spring Boot") ("React" OR "TypeScript") ("Jakarta" OR "Indonesia" OR "Remote")
site:glints.com ("Full Stack" OR "Fullstack") ("Golang" OR "Java") ("React" OR "TypeScript") ("Jakarta" OR "Remote")
site:dealls.com ("Full Stack Engineer" OR "Product Engineer") ("Golang" OR "React")
```

### Priority 4: Developer Tooling, Platform Engineering & Technical Mentorship

Wider net for platform, API tooling, solutions engineering, and backend team lead roles.

```
site:linkedin.com/jobs ("Platform Engineer" OR "Developer Experience" OR "Solutions Engineer" OR "Tech Lead") ("Golang" OR "Java Spring Boot") ("Jakarta" OR "Indonesia")
site:id.jobstreet.com ("Lead Backend" OR "Senior Software Engineer") ("Golang" OR "Java") Jakarta
site:kalibrr.com ("Solutions Engineer" OR "Technical Consultant") ("API" OR "Java" OR "Golang") Jakarta
```

## Location Filter

When evaluating results, verify the job location matches your preferences:
- **Ideal (PASS):**
  - Jakarta & Jabodetabek (South Jakarta, Central Jakarta, West/East/North Jakarta, Depok, Bekasi, Tangerang, Bogor) & West Java (Hybrid or On-site)
  - Fully Remote (Indonesia, SEA/APAC, or Global time-zone compatible)
- **Acceptable (PASS):**
  - Other major Indonesian tech hubs (Bandung, Yogyakarta, Bali, Surabaya)
- **Borderline (FLAG):**
  - Roles requiring frequent domestic/regional travel (>25%) or strict US/EU night-shift overlap for remote roles
- **Too far / Deal-breaker (FAIL):**
  - On-site roles outside Indonesia that do not provide visa sponsorship or relocation support

## Language Filter

Your working languages and levels are in CLAUDE.md's Languages table (Indonesian: Native/Bilingual; English: Professional Working). Apply `04-job-evaluation.md`'s Language Gate: a posting requiring a language not declared at all (e.g., Mandarin, Japanese, Danish) as a mandatory job condition is excluded; a posting requiring native/C2 English is flagged for your judgment rather than silently dropped.

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries
