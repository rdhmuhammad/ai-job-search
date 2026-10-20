# /html-interview - Generate Interactive Interview Questions Dashboard

Generate a self-contained, interactive HTML web dashboard from interview preparation packs under `documents/applications/` and tracker records in `job_search_tracker.csv`. The output is an interactive web page that syncs progress (checked questions and candidate notes) directly to `reports/interview_progress.json`, allowing you to navigate interview questions by company, practice talking points, and checklist mastered questions.

## Step 0: Parse Arguments

- No argument → output to `reports/interview-dashboard.html` and sync with `reports/interview_progress.json`
- `--serve` or `-s` → launch the live local synchronization server (`python tools/build_interview_dashboard.py --serve`) on `http://localhost:8765`, enabling automatic background saving to `reports/interview_progress.json` on every check or note edit
- A path argument (e.g. `/html-interview ~/Desktop/interview.html`) → use that path
- `--open` flag → after writing or starting the server, open the dashboard in your default browser

Create `reports/` if it does not exist.

---

## Step 1: Collect Interview & Application Data

Scan `documents/applications/*/`:

1. **Company & Application Metadata:**
   - Match each application folder to its corresponding record in `job_search_tracker.csv` (company name, role, sector, channel, status, fit_rating, source URL).
   - If not in the tracker, extract metadata from `job_posting.md` or folder name conventions (`<company>_<role>`).

2. **Interview Preparation Packs:**
   - Discover all interview preparation files under each application folder: `interview_prep_*.md`, `*interview*.md`, or `*prep*.md`.
   - If an application folder lacks an interview pack, surface it with status `Prep Needed` and remind the user to run `/interview <company>`.

---

## Step 2: Extract & Structure Questions

Parse the interview packs into structured question models with deterministic IDs:

1. **Question Types & Categories:**
   - **High-Priority Technical & Architecture:** Probed competencies, distributed systems, Golang concurrency, vector retrieval, and architectural trade-offs.
   - **STAR Behavioral Stories:** Structured Situation, Task, Action, Result breakdowns matched to candidate experience.
   - **Tough Questions & Honest Bridge Answers:** Probes on motivation ("Why this company?"), domain gaps, conflict resolution, and weakness.
   - **Smart Questions to Ask Interviewer:** Reverse interview inquiries on architecture, evaluation gates, and engineering cadence.

2. **Deterministic Question Identifiers:**
   - Assign stable keys (`{company_slug}-{type}-{index}`) so browser `localStorage` retains checked status and candidate notes across re-generation.

---

## Step 3: Generate the Interactive HTML Web Dashboard

Run `python tools/build_interview_dashboard.py --out <output_path>` or emit a single self-contained HTML file.

All styling is inline CSS (`<style>`), all interactivity is inline JavaScript (`<script>`). Fully functional offline without external CDNs.

### Key Capabilities:

- **Company Navigation (Sidebar):** Navigate between all tracked companies, displaying company logo/avatar initials, target role, sector badge, application status pill, and a live progress bar.
- **Interactive Checklist ("checklist current question"):**
  - Checkboxes to mark questions as "Practiced / Mastered".
  - Instant visual feedback: status badge updates, progress bars animate, card accents change.
  - Automatically saves state to `reports/interview_progress.json` (and `localStorage`).
- **Dynamic Progress Metrics:**
  - Global question count, mastered count, and preparedness rate percentage.
  - Per-company progress metrics and progress bars pre-calculated from `reports/interview_progress.json`.
- **Filters & Search:**
  - Real-time search across questions, categories, and answers.
  - Filter by checklist status: All, To Practice (unchecked), Mastered (checked).
  - Category pill filter for granular focus.
- **Personal Practice Notes:**
  - Auto-saving textarea on each question card to record delivery tips, STAR metrics, and mock feedback, persisted directly to `reports/interview_progress.json`.
- **JSON Storage & Live Server:**
  - **Live Auto-Save:** Running `python tools/build_interview_dashboard.py --serve` runs a lightweight local server where every check and note stroke writes to `reports/interview_progress.json`.
  - **Manual Save / Export:** One-click "Save to JSON" button writes or prompts direct save via File System Access API.
  - Pre-seeded build: re-running `/html-interview` reads `reports/interview_progress.json` and embeds your latest progress into the generated HTML file.

---

## Step 4: Write and Confirm

Write the file to `<output_path>` using `python tools/build_interview_dashboard.py`.

Then present:

> **Interview Dashboard generated:** `<output path>`
>
> Open it in any browser — no server needed.
>
> **Summary:**
> - Companies tracked: N
> - Total interview questions: N (Technical, STAR stories, Tough probes, Reverse inquiries)
> - Progress tracking: Stored locally in your browser
>
> Re-run `/html-interview` any time after running `/interview <company>` to update your questions.

---

## Design Principles

- **Self-contained.** One file, 100% offline — zero external CDN scripts or stylesheet dependencies.
- **State persistence.** Checkbox states and candidate notes persist in browser `localStorage`.
- **Idempotent.** Re-running updates questions without wiping candidate checklist progress or notes.
- **Multi-company navigation.** Effortlessly switch between companies and review stage-specific prep packs.
