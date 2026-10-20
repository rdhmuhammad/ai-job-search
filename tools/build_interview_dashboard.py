#!/usr/bin/env python3
"""Build interactive interview questions dashboard.

Scans `documents/applications/` and `job_search_tracker.csv`, extracts all
interview questions and preparation materials across companies, and compiles a
self-contained HTML dashboard with company navigation and interactive checklist
functionality that syncs with `reports/interview_progress.json`.

Usage:
    python tools/build_interview_dashboard.py [--out reports/interview-dashboard.html] [--open]
    python tools/build_interview_dashboard.py --serve [--port 8765] [--open]
"""

import argparse
import csv
import glob
import html
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text into a URL- and ID-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-') or 'item'


def format_markdown_body(md_text: str) -> str:
    """Convert basic markdown elements in question bodies into safe semantic HTML."""
    if not md_text:
        return ""

    lines = md_text.splitlines()
    html_parts = []
    in_ul = False
    in_ol = False
    in_code = False
    code_block_lines = []
    
    def close_lists():
        nonlocal in_ul, in_ol
        res = []
        if in_ul:
            res.append('</ul>')
            in_ul = False
        if in_ol:
            res.append('</ol>')
            in_ol = False
        return res

    for line in lines:
        stripped = line.strip()

        # Code block fence
        if stripped.startswith('```'):
            if in_code:
                html_parts.extend(close_lists())
                code_content = html.escape('\n'.join(code_block_lines))
                html_parts.append(f'<pre><code>{code_content}</code></pre>')
                code_block_lines = []
                in_code = False
            else:
                html_parts.extend(close_lists())
                in_code = True
                code_block_lines = []
            continue

        if in_code:
            code_block_lines.append(line)
            continue

        # Blank line
        if not stripped:
            html_parts.extend(close_lists())
            continue

        # Blockquote: > text
        if stripped.startswith('>'):
            html_parts.extend(close_lists())
            quote_text = html.escape(stripped.lstrip('>').strip())
            quote_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', quote_text)
            quote_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', quote_text)
            html_parts.append(f'<div class="callout-quote"><div class="quote-icon">💬</div><div class="quote-text">{quote_text}</div></div>')
            continue

        # Bullet list: - or *
        bullet_m = re.match(r'^(?:-|\*)\s+(.*)$', stripped)
        if bullet_m:
            if in_ol:
                html_parts.append('</ol>')
                in_ol = False
            if not in_ul:
                html_parts.append('<ul class="prep-bullet-list">')
                in_ul = True
            item_text = html.escape(bullet_m.group(1))
            item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', item_text)
            item_text = re.sub(r'`(.*?)`', r'<code>\1</code>', item_text)
            html_parts.append(f'<li>{item_text}</li>')
            continue

        # Numbered list: 1. or 2.
        ol_m = re.match(r'^([0-9]+)\.\s+(.*)$', stripped)
        if ol_m:
            if in_ul:
                html_parts.append('</ul>')
                in_ul = False
            if not in_ol:
                html_parts.append('<ol class="prep-numbered-list">')
                in_ol = True
            item_text = html.escape(ol_m.group(2))
            item_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', item_text)
            item_text = re.sub(r'`(.*?)`', r'<code>\1</code>', item_text)
            html_parts.append(f'<li>{item_text}</li>')
            continue

        # Probing header callout: *What they are probing:* ...
        probing_m = re.match(r'^\*What they are probing:\*\s*(.*)$', stripped, re.IGNORECASE)
        if probing_m:
            html_parts.extend(close_lists())
            probing_text = html.escape(probing_m.group(1).rstrip('*'))
            html_parts.append(f'''<div class="probing-box">
              <span class="probing-icon">🎯</span>
              <div class="probing-content">
                <strong>What they are probing:</strong> {probing_text}
              </div>
            </div>''')
            continue

        # Subheaders inside question body: **Key Talking Points:**
        subhead_m = re.match(r'^\*\*(.*?)\*\*$', stripped)
        if subhead_m:
            html_parts.extend(close_lists())
            subhead_text = html.escape(subhead_m.group(1))
            html_parts.append(f'<h5 class="body-subhead">{subhead_text}</h5>')
            continue

        # Normal paragraph
        html_parts.extend(close_lists())
        para_text = html.escape(stripped)
        para_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', para_text)
        para_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', para_text)
        para_text = re.sub(r'`(.*?)`', r'<code>\1</code>', para_text)
        html_parts.append(f'<p class="prep-para">{para_text}</p>')

    if in_code and code_block_lines:
        code_content = html.escape('\n'.join(code_block_lines))
        html_parts.append(f'<pre><code>{code_content}</code></pre>')

    html_parts.extend(close_lists())
    return '\n'.join(html_parts)


def parse_star_story(body_text: str) -> dict:
    """Extract Situation, Task, Action, Result components if present."""
    star_regex = re.compile(
        r'-\s+\*\*Situation:\*\*\s*(.*?)\n'
        r'-\s+\*\*Task:\*\*\s*(.*?)\n'
        r'-\s+\*\*Action:\*\*\s*(.*?)\n'
        r'-\s+\*\*Result:\*\*\s*(.*?)(?=\n-|\n#|\Z)',
        re.DOTALL | re.IGNORECASE
    )
    match = star_regex.search(body_text)
    if match:
        s, t, a, r = match.groups()
        return {
            'situation': s.strip(),
            'task': t.strip(),
            'action': a.strip(),
            'result': r.strip()
        }
    return None


def parse_interview_file(file_path: Path, company_slug: str) -> list:
    """Parse an interview prep markdown file into structured questions."""
    text = file_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    questions = []

    current_major_section = 'General'
    current_category = 'General'
    q_counter = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Major section: ## 3. High-Priority Technical & Architectural Questions
        sec_m = re.match(r'^##\s+(?:[0-9]+\.\s*)?(.*)$', line)
        if sec_m:
            current_major_section = sec_m.group(1).strip()
            current_category = current_major_section
            i += 1
            continue

        # Subcategory: ### Category A: High-Concurrency Golang & Distributed Systems
        cat_m = re.match(r'^###\s+Category\s+[A-Z0-9]+:\s*(.*)$', line, re.IGNORECASE)
        if cat_m:
            current_category = cat_m.group(1).strip()
            i += 1
            continue

        # Pattern 1: Technical question (#### Q1: "..." or ### Q1: ...)
        q_m = re.match(r'^#{3,4}\s+Q([0-9]+):\s*[\"“]?(.*?)[\"”]?\s*$', line)
        if q_m:
            q_num = q_m.group(1)
            q_title = q_m.group(2).strip()
            body_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^#{2,4}\s+', lines[i]):
                body_lines.append(lines[i])
                i += 1
            raw_body = '\n'.join(body_lines).strip()
            q_counter += 1
            
            probing = ""
            probing_search = re.search(r'\*What they are probing:\*\s*(.*?)(?:\n\n|\n\*\*|\Z)', raw_body, re.DOTALL | re.IGNORECASE)
            if probing_search:
                probing = probing_search.group(1).strip()

            questions.append({
                'id': f"{company_slug}-tech-{q_num}",
                'type': 'technical',
                'badge': 'Technical',
                'badge_class': 'badge-tech',
                'q_num': f'Q{q_num}',
                'title': q_title,
                'category': current_category,
                'probing': probing,
                'body_raw': raw_body,
                'body_html': format_markdown_body(raw_body),
                'star_data': None,
                'source_file': file_path.name
            })
            continue

        # Pattern 2: STAR Story (### STAR Story 1: ...)
        star_m = re.match(r'^#{3,4}\s+STAR\s+Story\s+([0-9]+):\s*(.*)$', line, re.IGNORECASE)
        if star_m:
            s_num = star_m.group(1)
            s_title = star_m.group(2).strip()
            body_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^#{2,4}\s+', lines[i]):
                body_lines.append(lines[i])
                i += 1
            raw_body = '\n'.join(body_lines).strip()
            star_parts = parse_star_story(raw_body)
            q_counter += 1

            questions.append({
                'id': f"{company_slug}-star-{s_num}",
                'type': 'star',
                'badge': 'STAR Story',
                'badge_class': 'badge-star',
                'q_num': f'STAR {s_num}',
                'title': s_title,
                'category': 'STAR Behavioral Stories',
                'probing': 'Demonstrates competency through structured Situation, Task, Action, and Result.',
                'body_raw': raw_body,
                'body_html': format_markdown_body(raw_body),
                'star_data': star_parts,
                'source_file': file_path.name
            })
            continue

        # Pattern 3: Tough question (### "Why Binance specifically?" or ### "...")
        tough_m = re.match(r'^#{3,4}\s+[\"“](.*?)[\"”]\s*$', line)
        if tough_m and not line.startswith('### Category'):
            t_title = tough_m.group(1).strip()
            body_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^#{2,4}\s+', lines[i]):
                body_lines.append(lines[i])
                i += 1
            raw_body = '\n'.join(body_lines).strip()
            q_counter += 1

            questions.append({
                'id': f"{company_slug}-tough-{q_counter}",
                'type': 'tough',
                'badge': 'Tough Question',
                'badge_class': 'badge-tough',
                'q_num': f'Tough {q_counter}',
                'title': t_title,
                'category': 'Tough & Bridge Questions',
                'probing': 'Probes motivation, company alignment, potential gaps, and conflict resolution.',
                'body_raw': raw_body,
                'body_html': format_markdown_body(raw_body),
                'star_data': None,
                'source_file': file_path.name
            })
            continue

        # Pattern 4: Smart Questions to Ask Interviewer in Section 6
        if 'Questions to Ask' in current_major_section:
            rev_m = re.match(r'^([0-9]+)\.\s+\*\*(.*?)\*\*:?\s*$', line)
            if rev_m:
                r_num = rev_m.group(1)
                r_topic = rev_m.group(2).strip()
                body_lines = []
                i += 1
                while i < len(lines) and not re.match(r'^(?:[0-9]+\.\s+\*\*|##)', lines[i]):
                    body_lines.append(lines[i])
                    i += 1
                r_body = '\n'.join(body_lines).strip()
                q_text_m = re.search(r'[\*\"“\']+(.+?)[\*\"”\']+', r_body)
                title = q_text_m.group(1) if q_text_m else r_topic
                q_counter += 1

                questions.append({
                    'id': f"{company_slug}-ask-{r_num}",
                    'type': 'reverse',
                    'badge': 'Questions to Ask',
                    'badge_class': 'badge-reverse',
                    'q_num': f'Ask {r_num}',
                    'title': title,
                    'topic': r_topic,
                    'category': 'Smart Questions to Ask Interviewer',
                    'probing': f'Strategic reverse interview inquiry on {r_topic}. Signals seniority and architectural curiosity.',
                    'body_raw': r_body,
                    'body_html': format_markdown_body(r_body),
                    'star_data': None,
                    'source_file': file_path.name
                })
                continue

        i += 1

    return questions


def load_application_data(repo_root: Path):
    """Scan documents/applications and tracker to compile company prep models."""
    csv_path = repo_root / 'job_search_tracker.csv'
    tracker_rows = []
    if csv_path.exists():
        with open(csv_path, mode='r', encoding='utf-8') as f:
            tracker_rows = list(csv.DictReader(f))

    apps_dir = repo_root / 'documents' / 'applications'
    companies = []

    for app_path in sorted(apps_dir.iterdir()):
        if not app_path.is_dir() or app_path.name.startswith('.'):
            continue

        folder_name = app_path.name
        
        matched_row = None
        for r in tracker_rows:
            comp_clean = re.sub(r'[^\w]', '', r.get('company', '').lower())
            folder_clean = re.sub(r'[^\w]', '', folder_name.lower())
            if comp_clean and comp_clean in folder_clean:
                matched_row = r
                break

        posting_file = app_path / 'job_posting.md'
        comp_display = ""
        role_display = ""
        sector_display = ""
        channel_display = ""
        status_display = "applied"
        fit_rating = 85
        source_url = ""

        if posting_file.exists():
            posting_text = posting_file.read_text(encoding='utf-8')
            c_m = re.search(r'-\s+\*\*Company:\*\*\s*(.*?)$', posting_text, re.MULTILINE)
            if c_m:
                comp_display = c_m.group(1).strip()
            r_m = re.search(r'^#\s+(.*?)$', posting_text, re.MULTILINE)
            if r_m:
                role_display = r_m.group(1).strip()
            u_m = re.search(r'-\s+\*\*URL:\*\*\s*(https?://[^\s]+)', posting_text)
            if u_m:
                source_url = u_m.group(1).strip()
            s_m = re.search(r'-\s+\*\*Industries:\*\*\s*(.*?)$', posting_text, re.MULTILINE)
            if s_m:
                sector_display = s_m.group(1).strip()
            rk_m = re.search(r'-\s+\*\*Rank Score:\*\*\s*([0-9]+)', posting_text)
            if rk_m:
                try:
                    fit_rating = int(rk_m.group(1))
                except ValueError:
                    pass

        if matched_row:
            comp_display = matched_row.get('company') or comp_display
            role_display = matched_row.get('role') or role_display
            sector_display = matched_row.get('sector') or sector_display
            channel_display = matched_row.get('channel') or channel_display
            status_display = matched_row.get('status') or status_display
            source_url = matched_row.get('source') or source_url
            try:
                fit_rating = int(matched_row.get('fit_rating') or fit_rating)
            except ValueError:
                pass

        if not comp_display:
            parts = folder_name.split('_')
            comp_display = parts[0].replace('-', ' ').title()
        if not role_display:
            parts = folder_name.split('_')
            role_display = ' '.join(parts[1:]).replace('-', ' ').title() if len(parts) > 1 else 'Software Engineer'

        company_slug = slugify(comp_display)

        prep_files = sorted(list(app_path.glob('*interview*.md')) + list(app_path.glob('*prep*.md')))
        prep_files = sorted(list(set(prep_files)))

        questions = []
        for pf in prep_files:
            qs = parse_interview_file(pf, company_slug)
            questions.extend(qs)

        initials = "".join([part[0].upper() for part in re.split(r'[\s.-]+', comp_display) if part])[:2]
        if not initials:
            initials = "CO"

        categories = sorted(list(set(q['category'] for q in questions)))

        companies.append({
            'folder': folder_name,
            'name': comp_display,
            'slug': company_slug,
            'initials': initials,
            'role': role_display,
            'sector': sector_display or 'Technology / Distributed Systems',
            'channel': channel_display or 'Direct / Portal',
            'status': status_display.lower(),
            'fit_rating': fit_rating,
            'source_url': source_url,
            'prep_files_count': len(prep_files),
            'questions': questions,
            'categories': categories,
            'question_count': len(questions)
        })

    return companies


def load_progress_data(json_path: Path) -> dict:
    """Load existing progress (checked questions and personal notes) from JSON file."""
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'updated_at': data.get('updated_at', ''),
                    'checked_questions': set(data.get('checked_questions', [])),
                    'notes': data.get('notes', {})
                }
        except Exception as e:
            print(f"Warning: could not read {json_path}: {e}")
    return {'updated_at': '', 'checked_questions': set(), 'notes': {}}


def generate_interview_dashboard(repo_root: Path = None, output_path: Path = None, json_path: Path = None) -> str:
    """Build the interview questions dashboard HTML file pre-seeded with JSON progress."""
    if repo_root is None:
        repo_root = Path.cwd()

    reports_dir = repo_root / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        output_path = reports_dir / 'interview-dashboard.html'
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if json_path is None:
        json_path = reports_dir / 'interview_progress.json'

    # Load stored progress from JSON
    progress_data = load_progress_data(json_path)
    stored_checked = progress_data['checked_questions']
    stored_notes = progress_data['notes']

    companies = load_application_data(repo_root)

    total_companies = len(companies)
    total_questions = sum(c['question_count'] for c in companies)

    # Calculate initial checked counts per company from stored progress
    initial_total_checked = 0
    company_initial_checked = {}
    for c in companies:
        c_done = sum(1 for q in c['questions'] if q['id'] in stored_checked)
        company_initial_checked[c['slug']] = c_done
        initial_total_checked += c_done

    initial_global_pct = round((initial_total_checked / total_questions) * 100) if total_questions > 0 else 0

    # Build company sidebar items HTML
    company_nav_items = []
    for idx, c in enumerate(companies):
        c_slug = c['slug']
        active_class = "active" if idx == 0 else ""
        status_label = c['status'].capitalize()
        status_pill_class = f"pill-{c['status']}" if c['status'] in ['applied', 'drafted', 'interview', 'offer', 'hired', 'rejected'] else "pill-drafted"
        c_done = company_initial_checked.get(c_slug, 0)
        c_pct = round((c_done / c['question_count']) * 100) if c['question_count'] > 0 else 0
        
        company_nav_items.append(f'''
        <div class="company-nav-item {active_class}" data-company="{html.escape(c_slug)}" onclick="selectCompany('{html.escape(c_slug)}')">
          <div class="nav-avatar">{html.escape(c['initials'])}</div>
          <div class="nav-info">
            <div class="nav-name-row">
              <span class="nav-company-name">{html.escape(c['name'])}</span>
              <span class="pill {status_pill_class}">{html.escape(status_label)}</span>
            </div>
            <div class="nav-role" title="{html.escape(c['role'])}">{html.escape(c['role'])}</div>
            <div class="nav-meta-row">
              <span class="nav-count"><span class="company-checked-count" data-company-count="{html.escape(c_slug)}">{c_done}</span>/{c['question_count']} Practiced</span>
              <div class="nav-mini-progress">
                <div class="nav-mini-bar" data-company-bar="{html.escape(c_slug)}" style="width: {c_pct}%;"></div>
              </div>
            </div>
          </div>
        </div>
        ''')

    company_nav_html = '\n'.join(company_nav_items)

    # Build company main panels HTML
    company_panels = []

    for idx, c in enumerate(companies):
        c_slug = c['slug']
        display_style = "block" if idx == 0 else "none"
        c_done = company_initial_checked.get(c_slug, 0)
        c_pct = round((c_done / c['question_count']) * 100) if c['question_count'] > 0 else 0

        cat_pills = ['<button class="filter-pill active" onclick="filterCategory(\'all\', this)">All Categories</button>']
        for cat in c['categories']:
            cat_pills.append(f'<button class="filter-pill" onclick="filterCategory(\'{html.escape(cat)}\', this)">{html.escape(cat)}</button>')
        cat_pills_html = '\n'.join(cat_pills)

        q_cards = []
        for q in c['questions']:
            qid = q['id']
            is_checked = qid in stored_checked
            checked_attr = 'checked="checked"' if is_checked else ''
            card_practiced_class = 'practiced' if is_checked else ''
            badge_text = 'Mastered' if is_checked else 'To Practice'
            badge_class = 'status-indicator mastered' if is_checked else 'status-indicator to-practice'
            saved_note = stored_notes.get(qid, '')

            # STAR block rendering
            star_html = ""
            if q.get('star_data'):
                sd = q['star_data']
                star_html = f'''
                <div class="star-grid">
                  <div class="star-card star-situation">
                    <div class="star-badge">S • Situation</div>
                    <div class="star-text">{html.escape(sd.get('situation', ''))}</div>
                  </div>
                  <div class="star-card star-task">
                    <div class="star-badge">T • Task</div>
                    <div class="star-text">{html.escape(sd.get('task', ''))}</div>
                  </div>
                  <div class="star-card star-action">
                    <div class="star-badge">A • Action</div>
                    <div class="star-text">{html.escape(sd.get('action', ''))}</div>
                  </div>
                  <div class="star-card star-result">
                    <div class="star-badge">R • Result</div>
                    <div class="star-text">{html.escape(sd.get('result', ''))}</div>
                  </div>
                </div>
                '''

            # Reverse question quote
            reverse_quote_html = ""
            if q['type'] == 'reverse' and q.get('topic'):
                reverse_quote_html = f'''
                <div class="reverse-header">
                  <span class="reverse-tag">Reverse Interview Inquiry</span>
                  <span class="reverse-topic">Topic: {html.escape(q['topic'])}</span>
                </div>
                '''

            q_cards.append(f'''
            <div class="question-card {card_practiced_class}" id="card-{qid}" data-qid="{qid}" data-company="{c_slug}" data-category="{html.escape(q['category'])}" data-type="{q['type']}">
              <div class="question-header" onclick="toggleCard('{qid}')">
                <div class="checkbox-container" onclick="event.stopPropagation();">
                  <input type="checkbox" id="check-{qid}" class="prep-checkbox" data-qid="{qid}" {checked_attr} onchange="toggleQuestionCheck('{qid}')">
                  <label for="check-{qid}" class="custom-checkbox" title="Mark as Practiced"></label>
                </div>
                
                <div class="q-header-meta">
                  <div class="q-badges">
                    <span class="q-badge {q['badge_class']}">{html.escape(q['badge'])}</span>
                    <span class="q-category-tag">{html.escape(q['category'])}</span>
                    <span class="q-num-pill">{html.escape(q['q_num'])}</span>
                  </div>
                  <h3 class="q-title" id="title-{qid}">{html.escape(q['title'])}</h3>
                </div>

                <div class="q-status-badge">
                  <span class="{badge_class}" id="badge-{qid}">{badge_text}</span>
                  <button class="btn-toggle-chevron" aria-label="Expand/Collapse">
                    <svg class="chevron-icon" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                  </button>
                </div>
              </div>

              <div class="question-body" id="body-{qid}">
                {q['probing'] and f"""<div class="probing-box"><span class="probing-icon">🎯</span><div class="probing-content"><strong>What they are probing:</strong> {html.escape(q['probing'])}</div></div>""" or ""}
                {reverse_quote_html}
                {star_html}
                <div class="body-content">
                  {q['body_html']}
                </div>

                <!-- Personal Practice Notes Area -->
                <div class="notes-section">
                  <div class="notes-header">
                    <span>✍️ Personal Practice Notes & Delivery Reminders</span>
                    <span class="notes-auto-save" id="notes-status-{qid}">Stored in reports/interview_progress.json</span>
                  </div>
                  <textarea class="notes-textarea" id="note-{qid}" data-qid="{qid}" placeholder="Jot down notes, metrics from your STAR stories, or interview rehearsal feedback (persisted to reports/interview_progress.json)..." oninput="saveNote('{qid}')">{html.escape(saved_note)}</textarea>
                </div>
              </div>
            </div>
            ''')

        cards_html = '\n'.join(q_cards) if q_cards else '<div class="empty-state">No interview questions found for this company yet. Run <code>/interview</code> to generate a preparation pack.</div>'

        source_link_html = f'<a class="comp-source-link" href="{html.escape(c["source_url"])}" target="_blank" rel="noopener noreferrer">View Original Posting ↗</a>' if c['source_url'] else ""

        company_panels.append(f'''
        <div class="company-panel" id="panel-{c_slug}" style="display: {display_style};" data-company="{c_slug}">
          <!-- Company Banner -->
          <div class="company-banner">
            <div class="banner-main">
              <div class="banner-title-row">
                <h2>{html.escape(c['name'])}</h2>
                <span class="pill pill-{c['status']}">{html.escape(c['status'].capitalize())}</span>
                <span class="fit-score-badge">Fit Score: {c['fit_rating']}/100</span>
              </div>
              <div class="banner-role">{html.escape(c['role'])}</div>
              <div class="banner-meta">
                <span>🏢 {html.escape(c['sector'])}</span>
                <span>📡 {html.escape(c['channel'])}</span>
                <span>📁 {html.escape(c['folder'])}</span>
                {source_link_html}
              </div>
            </div>

            <!-- Company Progress Card -->
            <div class="banner-progress-card">
              <div class="progress-title">Preparation Progress</div>
              <div class="progress-stats">
                <span class="progress-big-number" id="company-progress-num-{c_slug}">{c_done}</span>
                <span class="progress-total">/ {c['question_count']} Mastered</span>
                <span class="progress-pct" id="company-progress-pct-{c_slug}">({c_pct}%)</span>
              </div>
              <div class="progress-bar-container">
                <div class="progress-bar-fill" id="company-progress-bar-{c_slug}" style="width: {c_pct}%;"></div>
              </div>
            </div>
          </div>

          <!-- Controls Bar -->
          <div class="panel-controls">
            <div class="category-pills-scroll">
              {cat_pills_html}
            </div>

            <div class="quick-actions">
              <button class="btn-action" onclick="toggleExpandAll('{c_slug}', true)">Expand All</button>
              <button class="btn-action" onclick="toggleExpandAll('{c_slug}', false)">Collapse All</button>
              <button class="btn-action btn-mark" onclick="markAllCompany('{c_slug}', true)">Mark All Done</button>
              <button class="btn-action" onclick="markAllCompany('{c_slug}', false)">Unmark All</button>
            </div>
          </div>

          <!-- Question Cards Container -->
          <div class="question-list" id="list-{c_slug}">
            {cards_html}
          </div>
        </div>
        ''')

    panels_html = '\n'.join(company_panels)

    # Serializable JSON state preloaded
    initial_json_dump = json.dumps({
        'checked_questions': list(stored_checked),
        'notes': stored_notes
    })

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Interview Questions & Prep Dashboard</title>
  <style>
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-card: #ffffff;
      --card-bg: #ffffff;
      --card-border: #e2e8f0;
      --text: #0f172a;
      --text-muted: #64748b;
      --text-light: #94a3b8;
      --primary: #3b82f6;
      --primary-dark: #1d4ed8;
      --primary-light: #eff6ff;
      --success: #10b981;
      --success-light: #ecfdf5;
      --amber: #f59e0b;
      --amber-light: #fffbeb;
      --purple: #8b5cf6;
      --purple-light: #f5f3ff;
      --rose: #f43f5e;
      --rose-light: #fff1f2;
      --border: #e2e8f0;
      --sidebar-bg: #0f172a;
      --sidebar-card: #1e293b;
      --sidebar-active: #334155;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: #f8fafc;
      color: var(--text);
      font-family: var(--font-family);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Layout Shell */
    .app-header {{
      background-color: #0f172a;
      color: #ffffff;
      padding: 16px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      border-bottom: 1px solid #334155;
    }}

    .header-brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .header-icon {{
      font-size: 1.75rem;
    }}

    .header-title h1 {{
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}

    .header-title p {{
      font-size: 0.8125rem;
      color: var(--text-light);
    }}

    .global-stats {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    .stat-badge-item {{
      text-align: right;
    }}

    .stat-badge-val {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #ffffff;
      line-height: 1.1;
    }}

    .stat-badge-label {{
      font-size: 0.75rem;
      color: var(--text-light);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .global-progress-bar-wrap {{
      width: 140px;
      height: 8px;
      background: #334155;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 4px;
    }}

    .global-progress-bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #10b981);
      width: {initial_global_pct}%;
      transition: width 0.3s ease;
    }}

    /* Global Search & Sync Bar */
    .top-toolbar {{
      background: #ffffff;
      border-bottom: 1px solid var(--border);
      padding: 12px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .toolbar-left {{
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .search-box-wrap {{
      display: flex;
      align-items: center;
      background: #f1f5f9;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 6px 12px;
      width: 320px;
      max-width: 100%;
    }}

    .search-box-wrap svg {{
      width: 18px;
      height: 18px;
      color: var(--text-muted);
      margin-right: 8px;
    }}

    .search-input {{
      border: none;
      background: transparent;
      outline: none;
      width: 100%;
      font-size: 0.875rem;
      color: var(--text);
    }}

    .status-filter-pills {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .btn-status-filter {{
      border: 1px solid var(--border);
      background: #ffffff;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .btn-status-filter.active {{
      background: #0f172a;
      color: #ffffff;
      border-color: #0f172a;
    }}

    .toolbar-right {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    /* Sync Indicator */
    .sync-status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      background: #f1f5f9;
      color: #334155;
      border: 1px solid var(--border);
    }}

    .sync-status-pill.online {{
      background: #ecfdf5;
      color: #065f46;
      border-color: #a7f3d0;
    }}

    .sync-status-pill.saving {{
      background: #fffbeb;
      color: #92400e;
      border-color: #fde68a;
    }}

    .btn-secondary {{
      background: #f1f5f9;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .btn-secondary:hover {{
      background: #e2e8f0;
    }}

    .btn-primary {{
      background: #10b981;
      color: #ffffff;
      border: 1px solid #059669;
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 0.8125rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .btn-primary:hover {{
      background: #059669;
    }}

    /* Main Container */
    .app-main {{
      display: flex;
      flex: 1;
    }}

    /* Sidebar Navigation */
    .sidebar {{
      width: 320px;
      background: #0f172a;
      color: #ffffff;
      border-right: 1px solid #1e293b;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }}

    .sidebar-heading {{
      padding: 16px 20px 8px 20px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-light);
    }}

    .sidebar-list {{
      padding: 8px 12px;
      overflow-y: auto;
      flex: 1;
    }}

    .company-nav-item {{
      background: transparent;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      transition: background 0.15s ease;
      border: 1px solid transparent;
    }}

    .company-nav-item:hover {{
      background: rgba(255, 255, 255, 0.05);
    }}

    .company-nav-item.active {{
      background: #1e293b;
      border-color: #3b82f6;
    }}

    .nav-avatar {{
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, #3b82f6, #6366f1);
      color: #ffffff;
      font-weight: 700;
      font-size: 0.95rem;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}

    .nav-info {{
      flex: 1;
      min-width: 0;
    }}

    .nav-name-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 2px;
    }}

    .nav-company-name {{
      font-size: 0.9rem;
      font-weight: 600;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .nav-role {{
      font-size: 0.75rem;
      color: var(--text-light);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 6px;
    }}

    .nav-meta-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-light);
      gap: 8px;
    }}

    .nav-mini-progress {{
      flex: 1;
      height: 4px;
      background: #334155;
      border-radius: 2px;
      overflow: hidden;
    }}

    .nav-mini-bar {{
      height: 100%;
      background: #10b981;
      transition: width 0.3s ease;
    }}

    /* Main View Area */
    .content-area {{
      flex: 1;
      padding: 24px 32px;
      overflow-y: auto;
      max-width: 1100px;
    }}

    /* Company Banner */
    .company-banner {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }}

    .banner-main {{
      flex: 1;
      min-width: 280px;
    }}

    .banner-title-row {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 6px;
    }}

    .banner-title-row h2 {{
      font-size: 1.6rem;
      font-weight: 700;
      color: var(--text);
    }}

    .banner-role {{
      font-size: 1.05rem;
      font-weight: 500;
      color: #3b82f6;
      margin-bottom: 8px;
    }}

    .banner-meta {{
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
      font-size: 0.8125rem;
      color: var(--text-muted);
    }}

    .comp-source-link {{
      color: #2563eb;
      text-decoration: none;
      font-weight: 500;
    }}

    .comp-source-link:hover {{
      text-decoration: underline;
    }}

    .fit-score-badge {{
      background: #f0fdf4;
      color: #166534;
      border: 1px solid #bbf7d0;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
    }}

    .banner-progress-card {{
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px 20px;
      min-width: 240px;
      text-align: right;
    }}

    .progress-title {{
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }}

    .progress-stats {{
      display: flex;
      align-items: baseline;
      justify-content: flex-end;
      gap: 6px;
      margin-bottom: 8px;
    }}

    .progress-big-number {{
      font-size: 1.75rem;
      font-weight: 800;
      color: #0f172a;
      line-height: 1;
    }}

    .progress-total {{
      font-size: 0.875rem;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .progress-pct {{
      font-size: 0.875rem;
      font-weight: 700;
      color: #10b981;
    }}

    .progress-bar-container {{
      width: 100%;
      height: 8px;
      background: #e2e8f0;
      border-radius: 4px;
      overflow: hidden;
    }}

    .progress-bar-fill {{
      height: 100%;
      background: #10b981;
      transition: width 0.3s ease;
    }}

    /* Controls Bar */
    .panel-controls {{
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .category-pills-scroll {{
      display: flex;
      align-items: center;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 4px;
    }}

    .filter-pill {{
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text-muted);
      border-radius: 20px;
      padding: 5px 14px;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }}

    .filter-pill:hover {{
      background: #f1f5f9;
      color: var(--text);
    }}

    .filter-pill.active {{
      background: #3b82f6;
      color: #ffffff;
      border-color: #3b82f6;
    }}

    .quick-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .btn-action {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 5px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
    }}

    .btn-action:hover {{
      background: #f1f5f9;
      color: var(--text);
    }}

    .btn-action.btn-mark {{
      color: #059669;
      border-color: #a7f3d0;
      background: #ecfdf5;
    }}

    .btn-action.btn-mark:hover {{
      background: #d1fae5;
    }}

    /* Question Cards */
    .question-list {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .question-card {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      overflow: hidden;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    .question-card.practiced {{
      border-color: #a7f3d0;
      background: #fcfffd;
    }}

    .question-card.practiced .q-title {{
      color: #065f46;
    }}

    .question-header {{
      padding: 16px 20px;
      display: flex;
      align-items: flex-start;
      gap: 16px;
      cursor: pointer;
      user-select: none;
    }}

    .question-header:hover {{
      background: #fbfcfe;
    }}

    /* Checkbox Styling */
    .checkbox-container {{
      padding-top: 2px;
      display: flex;
      align-items: center;
    }}

    .prep-checkbox {{
      display: none;
    }}

    .custom-checkbox {{
      width: 22px;
      height: 22px;
      border: 2px solid #cbd5e1;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.15s ease;
      background: #ffffff;
    }}

    .prep-checkbox:checked + .custom-checkbox {{
      background: #10b981;
      border-color: #10b981;
    }}

    .prep-checkbox:checked + .custom-checkbox::after {{
      content: "";
      width: 6px;
      height: 11px;
      border: solid #ffffff;
      border-width: 0 2px 2px 0;
      transform: rotate(45deg);
      margin-bottom: 2px;
    }}

    .q-header-meta {{
      flex: 1;
      min-width: 0;
    }}

    .q-badges {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      flex-wrap: wrap;
    }}

    .q-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .badge-tech {{ background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }}
    .badge-star {{ background: #faf5ff; color: #7e22ce; border: 1px solid #e9d5ff; }}
    .badge-tough {{ background: #fff1f2; color: #be123c; border: 1px solid #fecdd3; }}
    .badge-reverse {{ background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }}

    .q-category-tag {{
      font-size: 0.75rem;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .q-num-pill {{
      font-size: 0.7rem;
      color: var(--text-light);
      background: #f1f5f9;
      padding: 1px 6px;
      border-radius: 4px;
    }}

    .q-title {{
      font-size: 1.05rem;
      font-weight: 600;
      line-height: 1.4;
      color: #1e293b;
    }}

    .q-status-badge {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding-top: 2px;
    }}

    .status-indicator {{
      font-size: 0.75rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 12px;
      white-space: nowrap;
    }}

    .status-indicator.to-practice {{
      background: #fef3c7;
      color: #92400e;
      border: 1px solid #fde68a;
    }}

    .status-indicator.mastered {{
      background: #d1fae5;
      color: #065f46;
      border: 1px solid #a7f3d0;
    }}

    .btn-toggle-chevron {{
      background: none;
      border: none;
      cursor: pointer;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      padding: 4px;
    }}

    .chevron-icon {{
      width: 18px;
      height: 18px;
      transition: transform 0.2s ease;
    }}

    .question-card.collapsed .chevron-icon {{
      transform: rotate(-90deg);
    }}

    .question-card.collapsed .question-body {{
      display: none;
    }}

    /* Card Body */
    .question-body {{
      padding: 0 20px 20px 58px;
      border-top: 1px solid #f1f5f9;
      background: #ffffff;
    }}

    .probing-box {{
      background: #f8fafc;
      border-left: 4px solid #3b82f6;
      padding: 12px 16px;
      border-radius: 0 8px 8px 0;
      margin: 16px 0;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      font-size: 0.875rem;
      color: #334155;
    }}

    .probing-icon {{
      font-size: 1.1rem;
    }}

    .reverse-header {{
      background: #ecfdf5;
      border: 1px solid #a7f3d0;
      padding: 8px 14px;
      border-radius: 6px;
      margin: 16px 0;
      display: flex;
      justify-content: space-between;
      font-size: 0.8125rem;
      color: #065f46;
      font-weight: 600;
    }}

    /* STAR Grid Layout */
    .star-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin: 16px 0;
    }}

    .star-card {{
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 14px;
    }}

    .star-situation {{ border-top: 3px solid #3b82f6; }}
    .star-task {{ border-top: 3px solid #f59e0b; }}
    .star-action {{ border-top: 3px solid #8b5cf6; }}
    .star-result {{ border-top: 3px solid #10b981; }}

    .star-badge {{
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
      color: var(--text-muted);
    }}

    .star-text {{
      font-size: 0.875rem;
      line-height: 1.45;
      color: #1e293b;
    }}

    /* Body Typography */
    .body-content {{
      font-size: 0.9rem;
      line-height: 1.6;
      color: #334155;
    }}

    .body-subhead {{
      font-size: 0.95rem;
      font-weight: 700;
      color: #0f172a;
      margin: 16px 0 8px 0;
    }}

    .prep-para {{
      margin-bottom: 10px;
    }}

    .prep-bullet-list, .prep-numbered-list {{
      margin: 8px 0 14px 20px;
    }}

    .prep-bullet-list li, .prep-numbered-list li {{
      margin-bottom: 6px;
    }}

    .callout-quote {{
      background: #f1f5f9;
      border-left: 4px solid #64748b;
      padding: 12px 16px;
      border-radius: 0 8px 8px 0;
      margin: 14px 0;
      display: flex;
      gap: 10px;
      font-style: italic;
      color: #1e293b;
    }}

    pre {{
      background: #0f172a;
      color: #f8fafc;
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 0.8125rem;
      overflow-x: auto;
      margin: 12px 0;
    }}

    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85em;
      background: #f1f5f9;
      color: #0f172a;
      padding: 2px 4px;
      border-radius: 4px;
    }}

    pre code {{
      background: transparent;
      color: inherit;
      padding: 0;
    }}

    /* Notes Area */
    .notes-section {{
      margin-top: 20px;
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
    }}

    .notes-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 8px;
    }}

    .notes-auto-save {{
      font-size: 0.7rem;
      color: #10b981;
    }}

    .notes-textarea {{
      width: 100%;
      min-height: 60px;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 12px;
      font-family: var(--font-family);
      font-size: 0.8125rem;
      color: var(--text);
      background: #ffffff;
      resize: vertical;
    }}

    .notes-textarea:focus {{
      outline: 2px solid #3b82f6;
      border-color: transparent;
    }}

    /* Status Pills */
    .pill {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: capitalize;
    }}

    .pill-drafted {{ background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; }}
    .pill-applied {{ background: #eff6ff; color: #3b82f6; border: 1px solid #bfdbfe; }}
    .pill-interview {{ background: #fffbeb; color: #f59e0b; border: 1px solid #fde68a; }}
    .pill-offer {{ background: #f5f3ff; color: #8b5cf6; border: 1px solid #ddd6fe; }}
    .pill-hired {{ background: #f0fdf4; color: #22c55e; border: 1px solid #bbf7d0; }}
    .pill-rejected {{ background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; }}

    .empty-state {{
      padding: 40px;
      text-align: center;
      background: #ffffff;
      border: 1px dashed var(--border);
      border-radius: 8px;
      color: var(--text-muted);
    }}

    /* Footer */
    footer {{
      background: #ffffff;
      border-top: 1px solid var(--border);
      text-align: center;
      padding: 16px;
      font-size: 0.8125rem;
      color: var(--text-muted);
    }}

    /* Responsive */
    @media (max-width: 900px) {{
      .app-main {{
        flex-direction: column;
      }}
      .sidebar {{
        width: 100%;
        max-height: 280px;
      }}
      .content-area {{
        padding: 16px;
      }}
      .question-body {{
        padding-left: 20px;
      }}
    }}

    @media print {{
      .sidebar, .top-toolbar, .quick-actions, .notes-section, .btn-toggle-chevron {{
        display: none !important;
      }}
      body {{
        background: #ffffff;
        color: #000000;
      }}
      .question-card {{
        break-inside: avoid;
        border: 1px solid #ccc;
        box-shadow: none;
      }}
      .question-body {{
        display: block !important;
      }}
    }}
  </style>
</head>
<body>
  <!-- Header Bar -->
  <header class="app-header">
    <div class="header-brand">
      <div class="header-icon">🎯</div>
      <div class="header-title">
        <h1>Interview Questions & Prep Dashboard</h1>
        <p>Interactive preparation checklist syncing with reports/interview_progress.json</p>
      </div>
    </div>

    <!-- Global Progress Summary -->
    <div class="global-stats">
      <div class="stat-badge-item">
        <div class="stat-badge-val" id="global-practiced-val">{initial_total_checked} / {total_questions}</div>
        <div class="stat-badge-label">Mastered / Total Questions</div>
        <div class="global-progress-bar-wrap">
          <div class="global-progress-bar-fill" id="global-progress-bar" style="width: {initial_global_pct}%;"></div>
        </div>
      </div>
      <div class="stat-badge-item">
        <div class="stat-badge-val" id="global-pct-val">{initial_global_pct}%</div>
        <div class="stat-badge-label">Preparedness Rate</div>
      </div>
    </div>
  </header>

  <!-- Top Toolbar (Search, Filter, Sync Status, Actions) -->
  <div class="top-toolbar">
    <div class="toolbar-left">
      <div class="search-box-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input type="text" id="globalSearchInput" class="search-input" placeholder="Search questions, technologies, STAR stories..." oninput="handleSearch()">
      </div>

      <div class="status-filter-pills">
        <button class="btn-status-filter active" data-filter="all" onclick="filterStatus('all', this)">All Questions</button>
        <button class="btn-status-filter" data-filter="unchecked" onclick="filterStatus('unchecked', this)">To Practice</button>
        <button class="btn-status-filter" data-filter="checked" onclick="filterStatus('checked', this)">Mastered</button>
      </div>
    </div>

    <div class="toolbar-right">
      <!-- Sync Status Pill -->
      <div class="sync-status-pill online" id="syncStatusPill" title="Status of sync with reports/interview_progress.json">
        <span id="syncDot">🟢</span>
        <span id="syncText">Syncing with reports/interview_progress.json</span>
      </div>

      <button class="btn-primary" onclick="syncNow()" title="Save all checked questions and notes to reports/interview_progress.json">
        <span>💾</span> Save to JSON
      </button>

      <button class="btn-secondary" onclick="exportChecklist()" title="Download progress JSON file">
        <span>📥</span> Export
      </button>

      <button class="btn-secondary" onclick="resetChecklist()" title="Clear checked questions">
        <span>🔄</span> Reset
      </button>
    </div>
  </div>

  <!-- App Main Content Area with Sidebar -->
  <div class="app-main">
    <!-- Company Sidebar Navigation -->
    <aside class="sidebar">
      <div class="sidebar-heading">Tracked Companies ({total_companies})</div>
      <div class="sidebar-list">
        {company_nav_html}
      </div>
    </aside>

    <!-- Main Content Panel -->
    <main class="content-area">
      {panels_html}
    </main>
  </div>

  <footer>
    Interactive Interview Prep Dashboard · Syncs with reports/interview_progress.json · 2026-10-20
  </footer>

  <!-- Application Logic & JSON Sync Engine -->
  <script>
    const INITIAL_DATA = {initial_json_dump};
    const STORAGE_KEY_PREFIX = 'interview_check_';
    const NOTES_KEY_PREFIX = 'interview_notes_';

    let currentCompany = '{companies[0]["slug"] if companies else ""}';
    let currentCategory = 'all';
    let currentStatusFilter = 'all';
    let searchQuery = '';
    let saveDebounceTimer = null;
    let syncApiEndpoint = '/api/progress';

    // Initialize application on load
    document.addEventListener('DOMContentLoaded', () => {{
      testServerConnection();
      restoreInitialState();
      updateAllProgress();
    }});

    // Test API connection to local server
    async function testServerConnection() {{
      const candidates = ['/api/progress', 'http://localhost:8765/api/progress'];
      for (const url of candidates) {{
        try {{
          const res = await fetch(url, {{ method: 'GET' }});
          if (res.ok) {{
            syncApiEndpoint = url;
            setSyncStatus('online', '🟢 Live Connected: reports/interview_progress.json');
            return;
          }}
        }} catch (e) {{}}
      }}
      setSyncStatus('offline', '📁 Local Mode (Click "Save to JSON" to write to reports)');
    }}

    function setSyncStatus(mode, text) {{
      const pill = document.getElementById('syncStatusPill');
      const textSpan = document.getElementById('syncText');
      if (pill) {{
        pill.className = 'sync-status-pill ' + mode;
      }}
      if (textSpan) {{
        textSpan.textContent = text;
      }}
    }}

    // Restore state from baked JSON data and localStorage fallback
    function restoreInitialState() {{
      // Pre-seed from INITIAL_DATA if present
      if (INITIAL_DATA && INITIAL_DATA.checked_questions) {{
        INITIAL_DATA.checked_questions.forEach(qid => {{
          const cb = document.getElementById('check-' + qid);
          if (cb) cb.checked = true;
          const card = document.getElementById('card-' + qid);
          const badge = document.getElementById('badge-' + qid);
          if (card) card.classList.add('practiced');
          if (badge) {{
            badge.textContent = 'Mastered';
            badge.className = 'status-indicator mastered';
          }}
        }});
      }}

      if (INITIAL_DATA && INITIAL_DATA.notes) {{
        for (const [qid, noteText] of Object.entries(INITIAL_DATA.notes)) {{
          const noteArea = document.getElementById('note-' + qid);
          if (noteArea && !noteArea.value) {{
            noteArea.value = noteText;
          }}
        }}
      }}

      // Restore any fresher changes from localStorage
      document.querySelectorAll('.prep-checkbox').forEach(cb => {{
        const qid = cb.getAttribute('data-qid');
        try {{
          const localVal = localStorage.getItem(STORAGE_KEY_PREFIX + qid);
          if (localVal !== null) {{
            const isChecked = (localVal === '1');
            cb.checked = isChecked;
            const card = document.getElementById('card-' + qid);
            const badge = document.getElementById('badge-' + qid);
            if (card) {{
              if (isChecked) card.classList.add('practiced');
              else card.classList.remove('practiced');
            }}
            if (badge) {{
              badge.textContent = isChecked ? 'Mastered' : 'To Practice';
              badge.className = isChecked ? 'status-indicator mastered' : 'status-indicator to-practice';
            }}
          }}
        }} catch (e) {{}}

        const noteArea = document.getElementById('note-' + qid);
        if (noteArea) {{
          try {{
            const localNote = localStorage.getItem(NOTES_KEY_PREFIX + qid);
            if (localNote !== null) {{
              noteArea.value = localNote;
            }}
          }} catch (e) {{}}
        }}
      }});
    }}

    // Select active company in sidebar
    function selectCompany(companySlug) {{
      currentCompany = companySlug;
      currentCategory = 'all';

      document.querySelectorAll('.company-nav-item').forEach(item => {{
        if (item.getAttribute('data-company') === companySlug) {{
          item.classList.add('active');
        }} else {{
          item.classList.remove('active');
        }}
      }});

      document.querySelectorAll('.company-panel').forEach(panel => {{
        if (panel.getAttribute('data-company') === companySlug) {{
          panel.style.display = 'block';
        }} else {{
          panel.style.display = 'none';
        }}
      }});

      const activePanel = document.getElementById('panel-' + companySlug);
      if (activePanel) {{
        activePanel.querySelectorAll('.filter-pill').forEach((pill, idx) => {{
          if (idx === 0) pill.classList.add('active');
          else pill.classList.remove('active');
        }});
      }}

      applyFilters();
    }}

    // Toggle card expansion
    function toggleCard(qid) {{
      const card = document.getElementById('card-' + qid);
      if (card) {{
        card.classList.toggle('collapsed');
      }}
    }}

    function toggleExpandAll(companySlug, expand) {{
      const panel = document.getElementById('panel-' + companySlug);
      if (!panel) return;
      panel.querySelectorAll('.question-card').forEach(card => {{
        if (expand) {{
          card.classList.remove('collapsed');
        }} else {{
          card.classList.add('collapsed');
        }}
      }});
    }}

    // Triggered when checking / unchecking a question
    function toggleQuestionCheck(qid) {{
      const checkbox = document.getElementById('check-' + qid);
      const isChecked = checkbox ? checkbox.checked : false;
      const card = document.getElementById('card-' + qid);
      const badge = document.getElementById('badge-' + qid);

      try {{
        localStorage.setItem(STORAGE_KEY_PREFIX + qid, isChecked ? '1' : '0');
      }} catch (e) {{}}

      if (card) {{
        if (isChecked) card.classList.add('practiced');
        else card.classList.remove('practiced');
      }}

      if (badge) {{
        if (isChecked) {{
          badge.textContent = 'Mastered';
          badge.className = 'status-indicator mastered';
        }} else {{
          badge.textContent = 'To Practice';
          badge.className = 'status-indicator to-practice';
        }}
      }}

      updateAllProgress();
      applyFilters();
      queueSaveToJson();
    }}

    // Triggered when typing personal notes
    function saveNote(qid) {{
      const noteArea = document.getElementById('note-' + qid);
      const statusSpan = document.getElementById('notes-status-' + qid);
      if (!noteArea) return;

      try {{
        localStorage.setItem(NOTES_KEY_PREFIX + qid, noteArea.value);
      }} catch (e) {{}}

      if (statusSpan) {{
        statusSpan.textContent = 'Saving...';
      }}

      queueSaveToJson(() => {{
        if (statusSpan) {{
          statusSpan.textContent = 'Stored in reports/interview_progress.json';
        }}
      }});
    }}

    // Debounced save to JSON file at reports/interview_progress.json
    function queueSaveToJson(callback) {{
      setSyncStatus('saving', '🟡 Storing to reports/interview_progress.json...');
      if (saveDebounceTimer) clearTimeout(saveDebounceTimer);
      saveDebounceTimer = setTimeout(() => {{
        persistToJsonFile().then(success => {{
          if (callback) callback();
        }});
      }}, 500);
    }}

    // Collect current state payload
    function getCurrentPayload() {{
      const checkedQuestions = [];
      document.querySelectorAll('.prep-checkbox').forEach(cb => {{
        if (cb.checked) {{
          checkedQuestions.push(cb.getAttribute('data-qid'));
        }}
      }});

      const notes = {{}};
      document.querySelectorAll('.notes-textarea').forEach(na => {{
        const text = na.value.trim();
        if (text) {{
          notes[na.getAttribute('data-qid')] = text;
        }}
      }});

      return {{
        updated_at: new Date().toISOString(),
        checked_questions: checkedQuestions,
        notes: notes
      }};
    }}

    // Persist payload to JSON file via API or File System Access
    async function persistToJsonFile() {{
      const payload = getCurrentPayload();

      // Attempt 1: If browser has granted a direct File System handle
      if (window.reportsJsonFileHandle) {{
        try {{
          const writable = await window.reportsJsonFileHandle.createWritable();
          await writable.write(JSON.stringify(payload, null, 2));
          await writable.close();
          setSyncStatus('online', '🟢 Direct Saved: reports/interview_progress.json (' + new Date().toLocaleTimeString() + ')');
          return true;
        }} catch (e) {{
          console.warn('File handle write error:', e);
        }}
      }}

      // Attempt 2: Via local server API endpoint (POST /api/progress)
      const endpoints = [syncApiEndpoint, 'http://localhost:8765/api/progress', '/api/progress'];
      for (const endpoint of endpoints) {{
        try {{
          const res = await fetch(endpoint, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(payload)
          }});
          if (res.ok) {{
            syncApiEndpoint = endpoint;
            setSyncStatus('online', '🟢 Stored to reports/interview_progress.json (' + new Date().toLocaleTimeString() + ')');
            return true;
          }}
        }} catch (e) {{}}
      }}

      // Fallback: Offline indicator
      setSyncStatus('offline', '📁 Cached locally (Click "Save to JSON" or run with --serve to persist)');
      return false;
    }}

    // Manual Save / Link action
    async function syncNow() {{
      const success = await persistToJsonFile();
      if (!success) {{
        // If server is not active, prompt to save / download or use showSaveFilePicker
        if ('showSaveFilePicker' in window) {{
          try {{
            window.reportsJsonFileHandle = await window.showSaveFilePicker({{
              suggestedName: 'interview_progress.json',
              types: [{{
                description: 'JSON Files',
                accept: {{ 'application/json': ['.json'] }}
              }}]
            }});
            await persistToJsonFile();
            alert('Connected to reports/interview_progress.json! All future marks and notes will write directly to this file.');
            return;
          }} catch (err) {{}}
        }}
        exportChecklist();
      }} else {{
        alert('Successfully saved current checklist progress and notes to reports/interview_progress.json!');
      }}
    }}

    // Mark all in active company
    function markAllCompany(companySlug, markDone) {{
      const panel = document.getElementById('panel-' + companySlug);
      if (!panel) return;
      panel.querySelectorAll('.prep-checkbox').forEach(cb => {{
        cb.checked = markDone;
        const qid = cb.getAttribute('data-qid');
        try {{
          localStorage.setItem(STORAGE_KEY_PREFIX + qid, markDone ? '1' : '0');
        }} catch (e) {{}}
        const card = document.getElementById('card-' + qid);
        const badge = document.getElementById('badge-' + qid);
        if (card) {{
          if (markDone) card.classList.add('practiced');
          else card.classList.remove('practiced');
        }}
        if (badge) {{
          badge.textContent = markDone ? 'Mastered' : 'To Practice';
          badge.className = markDone ? 'status-indicator mastered' : 'status-indicator to-practice';
        }}
      }});
      updateAllProgress();
      applyFilters();
      queueSaveToJson();
    }}

    // Update progress counters
    function updateAllProgress() {{
      const allCheckboxes = document.querySelectorAll('.prep-checkbox');
      let totalChecked = 0;
      const totalCount = allCheckboxes.length;

      const companyCounts = {{}};
      const companyChecked = {{}};

      allCheckboxes.forEach(cb => {{
        const qid = cb.getAttribute('data-qid');
        const card = document.getElementById('card-' + qid);
        if (!card) return;
        const company = card.getAttribute('data-company');

        companyCounts[company] = (companyCounts[company] || 0) + 1;
        if (cb.checked) {{
          totalChecked++;
          companyChecked[company] = (companyChecked[company] || 0) + 1;
        }}
      }});

      const globalPracticedVal = document.getElementById('global-practiced-val');
      const globalPctVal = document.getElementById('global-pct-val');
      const globalProgressBar = document.getElementById('global-progress-bar');
      const globalPct = totalCount > 0 ? Math.round((totalChecked / totalCount) * 100) : 0;

      if (globalPracticedVal) globalPracticedVal.textContent = `${{totalChecked}} / ${{totalCount}}`;
      if (globalPctVal) globalPctVal.textContent = `${{globalPct}}%`;
      if (globalProgressBar) globalProgressBar.style.width = `${{globalPct}}%`;

      for (const comp in companyCounts) {{
        const cTotal = companyCounts[comp] || 0;
        const cDone = companyChecked[comp] || 0;
        const cPct = cTotal > 0 ? Math.round((cDone / cTotal) * 100) : 0;

        const navCount = document.querySelector(`.company-checked-count[data-company-count="${{comp}}"]`);
        const navBar = document.querySelector(`.nav-mini-bar[data-company-bar="${{comp}}"]`);
        if (navCount) navCount.textContent = cDone;
        if (navBar) navBar.style.width = `${{cPct}}%`;

        const bannerNum = document.getElementById(`company-progress-num-${{comp}}`);
        const bannerPct = document.getElementById(`company-progress-pct-${{comp}}`);
        const bannerBar = document.getElementById(`company-progress-bar-${{comp}}`);
        if (bannerNum) bannerNum.textContent = cDone;
        if (bannerPct) bannerPct.textContent = `(${{cPct}}%)`;
        if (bannerBar) bannerBar.style.width = `${{cPct}}%`;
      }}
    }}

    function filterCategory(cat, btn) {{
      currentCategory = cat;
      const panel = document.getElementById('panel-' + currentCompany);
      if (panel) {{
        panel.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
        if (btn) btn.classList.add('active');
      }}
      applyFilters();
    }}

    function filterStatus(status, btn) {{
      currentStatusFilter = status;
      document.querySelectorAll('.btn-status-filter').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');
      applyFilters();
    }}

    function handleSearch() {{
      const searchBox = document.getElementById('globalSearchInput');
      searchQuery = (searchBox ? searchBox.value : '').toLowerCase().trim();
      applyFilters();
    }}

    function applyFilters() {{
      const panel = document.getElementById('panel-' + currentCompany);
      if (!panel) return;

      const cards = panel.querySelectorAll('.question-card');
      cards.forEach(card => {{
        const cardCat = card.getAttribute('data-category');
        const qid = card.getAttribute('data-qid');
        const checkbox = document.getElementById('check-' + qid);
        const isChecked = checkbox ? checkbox.checked : false;
        const textContent = card.textContent.toLowerCase();

        const matchesCat = (currentCategory === 'all' || cardCat === currentCategory);
        let matchesStatus = true;
        if (currentStatusFilter === 'checked') matchesStatus = isChecked;
        else if (currentStatusFilter === 'unchecked') matchesStatus = !isChecked;

        const matchesSearch = !searchQuery || textContent.includes(searchQuery);

        if (matchesCat && matchesStatus && matchesSearch) {{
          card.style.display = 'block';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}

    function exportChecklist() {{
      const exportData = getCurrentPayload();
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `interview_progress.json`;
      a.click();
      URL.revokeObjectURL(url);
    }}

    function resetChecklist() {{
      if (confirm('Are you sure you want to reset all checked questions and local notes in reports/interview_progress.json?')) {{
        document.querySelectorAll('.prep-checkbox').forEach(cb => {{
          cb.checked = false;
          const qid = cb.getAttribute('data-qid');
          try {{
            localStorage.removeItem(STORAGE_KEY_PREFIX + qid);
            localStorage.removeItem(NOTES_KEY_PREFIX + qid);
          }} catch (e) {{}}
          const card = document.getElementById('card-' + qid);
          const badge = document.getElementById('badge-' + qid);
          if (card) card.classList.remove('practiced');
          if (badge) {{
            badge.textContent = 'To Practice';
            badge.className = 'status-indicator to-practice';
          }}
          const noteArea = document.getElementById('note-' + qid);
          if (noteArea) noteArea.value = '';
        }});
        updateAllProgress();
        applyFilters();
        queueSaveToJson();
      }}
    }}
  </script>
</body>
</html>
'''

    output_path.write_text(full_html, encoding='utf-8')
    print(f"Generated interview dashboard: {output_path}")
    print(f"Loaded progress from: {json_path} ({len(stored_checked)} checked, {len(stored_notes)} notes)")
    print(f"Summary: {total_companies} companies, {total_questions} interview questions compiled.")
    return str(output_path)


class InterviewDashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler that serves the dashboard and handles JSON progress persistence."""

    def __init__(self, *args, json_path=None, html_path=None, repo_root=None, **kwargs):
        self.json_path = json_path
        self.html_path = html_path
        self.repo_root = repo_root
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path in ('/api/progress', '/api/progress/'):
            if self.json_path and self.json_path.exists():
                data = self.json_path.read_bytes()
            else:
                data = json.dumps({"updated_at": "", "checked_questions": [], "notes": {}}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path in ('/', '/index.html'):
            if self.html_path and self.html_path.exists():
                data = self.html_path.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        super().do_GET()

    def do_POST(self):
        if self.path in ('/api/progress', '/api/progress/'):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError("Payload must be a JSON object")

                self.json_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.json_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)

                checked_count = len(payload.get('checked_questions', []))
                notes_count = len(payload.get('notes', {}))
                print(f"[Sync] Saved {checked_count} checked questions, {notes_count} notes to {self.json_path.name}")

                resp = json.dumps({"status": "saved", "path": str(self.json_path)}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"error": str(e)}).encode('utf-8')
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            return

        self.send_response(404)
        self.end_headers()


def serve_dashboard(repo_root: Path, out_path: Path, json_path: Path, port: int = 8765, open_browser: bool = False):
    """Start local HTTP server with live JSON persistence."""
    generate_interview_dashboard(repo_root=repo_root, output_path=out_path, json_path=json_path)

    handler_factory = lambda *args, **kwargs: InterviewDashboardRequestHandler(
        *args,
        json_path=json_path,
        html_path=out_path,
        repo_root=repo_root,
        directory=str(repo_root),
        **kwargs
    )

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    try:
        with ReusableTCPServer(("", port), handler_factory) as httpd:
            url = f"http://localhost:{port}/"
            print(f"\n=======================================================")
            print(f"🎯 Interview Dashboard Live Server Running")
            print(f"   URL: {url}")
            print(f"   Sync File: {json_path}")
            print(f"   All checkbox and note changes save directly to JSON!")
            print(f"   Press Ctrl+C to stop.")
            print(f"=======================================================\n")
            if open_browser:
                webbrowser.open(url)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping interview dashboard server.")


def main():
    parser = argparse.ArgumentParser(description="Generate interactive interview questions dashboard.")
    parser.add_argument("--out", "-o", default=None, help="Output HTML file path (default: reports/interview-dashboard.html)")
    parser.add_argument("--json", "-j", default=None, help="Progress JSON file path (default: reports/interview_progress.json)")
    parser.add_argument("--serve", "-s", action="store_true", help="Start local live sync server")
    parser.add_argument("--port", "-p", type=int, default=8765, help="Port for local server (default: 8765)")
    parser.add_argument("--open", action="store_true", help="Hint to open the file in default browser")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    out_path = Path(args.out).resolve() if args.out else repo_root / "reports" / "interview-dashboard.html"
    json_path = Path(args.json).resolve() if args.json else repo_root / "reports" / "interview_progress.json"

    if args.serve:
        serve_dashboard(repo_root=repo_root, out_path=out_path, json_path=json_path, port=args.port, open_browser=args.open)
        return 0

    generated_path = generate_interview_dashboard(repo_root=repo_root, output_path=out_path, json_path=json_path)

    if args.open:
        print(f"Open '{generated_path}' in your browser to start practicing.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
