import csv
import html
import os

def generate_dashboard():
    csv_path = 'job_search_tracker.csv'
    out_path = 'reports/application-dashboard.html'

    with open(csv_path, mode='r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Sort rows newest first, then company
    rows.sort(key=lambda x: (x.get('date', ''), x.get('company', '')), reverse=True)

    sent_rows = [r for r in rows if r['status'].lower() != 'drafted']
    drafted_rows = [r for r in rows if r['status'].lower() == 'drafted']

    total_sent = len(sent_rows)
    total_drafted = len(drafted_rows)
    active_count = sum(1 for r in sent_rows if r['status'].lower() == 'applied')
    interview_count = sum(1 for r in sent_rows if r['status'].lower() == 'interview')
    offer_count = sum(1 for r in sent_rows if r['status'].lower() == 'offer')
    rejected_count = sum(1 for r in sent_rows if r['status'].lower() in ['rejected', 'no_response', 'withdrawn'])

    # Sector breakdown
    sectors = {}
    for r in rows:
        s = r.get('sector', 'Other')
        sectors[s] = sectors.get(s, 0) + 1
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)

    # Channel breakdown
    channels = {'online': 0, 'portal': 0, 'referral': 0, 'other': 0}
    for r in rows:
        c = r.get('channel', '').lower()
        if 'online' in c:
            channels['online'] += 1
        elif 'portal' in c:
            channels['portal'] += 1
        elif 'referral' in c:
            channels['referral'] += 1
        else:
            channels['other'] += 1

    # Unique sectors for dropdown
    unique_sectors = sorted(list(sectors.keys()))

    # Build Table rows HTML
    table_rows = []
    for r in rows:
        date = html.escape(r.get('date', '—'))
        deadline = html.escape(r.get('deadline', '') or '—')
        company = html.escape(r.get('company', '—'))
        role = html.escape(r.get('role', '—'))
        sector = html.escape(r.get('sector', '—'))
        channel = html.escape(r.get('channel', '—'))
        status_raw = r.get('status', 'drafted').lower()
        
        if status_raw == 'applied':
            pill_class = 'pill-active'
            pill_label = 'Active'
            data_status = 'active'
        elif status_raw == 'drafted':
            pill_class = 'pill-drafted'
            pill_label = 'Drafted'
            data_status = 'drafted'
        elif status_raw == 'interview':
            pill_class = 'pill-interview'
            pill_label = 'Interview'
            data_status = 'interview'
        elif status_raw == 'offer':
            pill_class = 'pill-offer'
            pill_label = 'Offer'
            data_status = 'offer'
        elif status_raw == 'hired':
            pill_class = 'pill-hired'
            pill_label = 'Hired'
            data_status = 'hired'
        else:
            pill_class = 'pill-rejected'
            pill_label = 'Rejected / Closed'
            data_status = 'rejected'

        notes = html.escape(r.get('notes', '—'))
        source_url = r.get('source', '')
        if source_url and source_url.startswith('http'):
            source_html = f'<a class="link-source" href="{html.escape(source_url)}" target="_blank" rel="noopener noreferrer">Posting ↗</a>'
        else:
            source_html = '—'

        table_rows.append(f'''            <tr data-status="{data_status}" data-sector="{sector}">
              <td>{date}</td>
              <td>{deadline}</td>
              <td><strong>{company}</strong></td>
              <td>{role}</td>
              <td>{sector}</td>
              <td>{channel}</td>
              <td><span class="pill {pill_class}">{pill_label}</span></td>
              <td>
                <div class="truncate" title="{notes}">
                  {notes}
                </div>
              </td>
              <td>
                {source_html}
              </td>
            </tr>''')

    rows_html = '\n'.join(table_rows)

    sector_options = '\n'.join([f'            <option value="{html.escape(s)}">{html.escape(s)}</option>' for s in unique_sectors])

    # Sector SVG chart rows
    max_sector_count = max(sectors.values()) if sectors else 1
    sector_svg_items = []
    y_pos = 16
    for s_name, s_count in sorted_sectors[:5]:
        bar_width = int((s_count / max_sector_count) * 260)
        sector_svg_items.append(f'''              <text x="0" y="{y_pos}" font-size="12" fill="#0f172a" font-weight="500">{html.escape(s_name)}</text>
              <rect x="0" y="{y_pos + 8}" width="{bar_width}" height="18" rx="4" fill="#3b82f6" />
              <text x="{bar_width + 10}" y="{y_pos + 22}" font-size="12" fill="#0f172a" font-weight="600">{s_count}</text>''')
        y_pos += 44

    sector_svg = '\n'.join(sector_svg_items)

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Job Search Dashboard</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --text-muted: #64748b;
      --color-drafted: #64748b;
      --color-active: #3b82f6;
      --color-interview: #f59e0b;
      --color-offer: #8b5cf6;
      --color-hired: #22c55e;
      --color-rejected: #ef4444;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      line-height: 1.5;
      padding: 24px;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}

    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    h1 {{
      font-size: 1.5rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .timestamp {{
      font-size: 0.875rem;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      border-left: 4px solid var(--border);
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    .stat-card.sent {{ border-left-color: var(--text); }}
    .stat-card.drafted {{ border-left-color: var(--color-drafted); }}
    .stat-card.active {{ border-left-color: var(--color-active); }}
    .stat-card.interview {{ border-left-color: var(--color-interview); }}
    .stat-card.offer {{ border-left-color: var(--color-offer); }}
    .stat-card.rejected {{ border-left-color: var(--color-rejected); }}

    .stat-value {{
      font-size: 1.75rem;
      font-weight: 700;
      line-height: 1.2;
    }}

    .stat-label {{
      font-size: 0.8125rem;
      color: var(--text-muted);
      margin-top: 4px;
      font-weight: 500;
    }}

    .charts-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .chart-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    .chart-card h3 {{
      font-size: 0.95rem;
      font-weight: 600;
      margin-bottom: 16px;
      color: var(--text);
    }}

    .chart-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 220px;
    }}

    .table-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      overflow: hidden;
      margin-bottom: 24px;
    }}

    .table-header {{
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      border-bottom: 1px solid var(--border);
    }}

    .table-header h3 {{
      font-size: 1.1rem;
      font-weight: 600;
    }}

    .filters-group {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }}

    .filter-input, .filter-select {{
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 0.875rem;
      color: var(--text);
      background-color: #fff;
    }}

    .filter-input {{
      min-width: 200px;
    }}

    .filter-input:focus, .filter-select:focus {{
      outline: 2px solid var(--color-active);
      border-color: transparent;
    }}

    .table-wrapper {{
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.875rem;
    }}

    th {{
      background: #f1f5f9;
      color: var(--text-muted);
      font-weight: 600;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}

    td {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
    }}

    tbody tr:nth-child(even) {{
      background-color: #fafbfc;
    }}

    tbody tr:hover {{
      background-color: #f1f5f9;
    }}

    .pill {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: capitalize;
    }}

    .pill-drafted {{ background: #f1f5f9; color: var(--color-drafted); border: 1px solid #cbd5e1; }}
    .pill-active {{ background: #eff6ff; color: var(--color-active); border: 1px solid #bfdbfe; }}
    .pill-interview {{ background: #fffbeb; color: var(--color-interview); border: 1px solid #fde68a; }}
    .pill-offer {{ background: #f5f3ff; color: var(--color-offer); border: 1px solid #ddd6fe; }}
    .pill-hired {{ background: #f0fdf4; color: var(--color-hired); border: 1px solid #bbf7d0; }}
    .pill-rejected {{ background: #fef2f2; color: var(--color-rejected); border: 1px solid #fecaca; }}

    .truncate {{
      max-width: 240px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      cursor: help;
    }}

    a.link-source {{
      color: #2563eb;
      text-decoration: none;
      font-weight: 500;
    }}

    a.link-source:hover {{
      text-decoration: underline;
    }}

    footer {{
      text-align: center;
      color: var(--text-muted);
      font-size: 0.8125rem;
      padding: 16px 0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1><span>🔍</span> Job Search Dashboard</h1>
      <div class="timestamp">Generated: 2026-10-20</div>
    </header>

    <!-- Stat Cards -->
    <section class="stats-grid">
      <div class="stat-card sent">
        <div class="stat-value">{total_sent}</div>
        <div class="stat-label">Sent</div>
      </div>
      <div class="stat-card drafted">
        <div class="stat-value">{total_drafted}</div>
        <div class="stat-label">Drafted</div>
      </div>
      <div class="stat-card active">
        <div class="stat-value">{active_count}</div>
        <div class="stat-label">Active</div>
      </div>
      <div class="stat-card interview">
        <div class="stat-value">{interview_count}</div>
        <div class="stat-label">Interview</div>
      </div>
      <div class="stat-card offer">
        <div class="stat-value">{offer_count}</div>
        <div class="stat-label">Offer</div>
      </div>
      <div class="stat-card rejected">
        <div class="stat-value">{rejected_count}</div>
        <div class="stat-label">Rejected / Closed</div>
      </div>
    </section>

    <!-- Charts Row -->
    <section class="charts-grid">
      <!-- Chart 1: Status Breakdown -->
      <div class="chart-card">
        <h3>Status Breakdown</h3>
        <div class="chart-container">
          <svg width="340" height="210" viewBox="0 0 340 210" role="img" aria-label="Status breakdown: {active_count} Active, {total_drafted} Drafted">
            <g transform="translate(100, 105)">
              <circle cx="0" cy="0" r="70" fill="none" stroke="#3b82f6" stroke-width="26" />
              <text x="0" y="5" text-anchor="middle" font-size="20" font-weight="700" fill="#0f172a">{total_sent}</text>
              <text x="0" y="24" text-anchor="middle" font-size="10" fill="#64748b">Total Sent</text>
            </g>
            <g transform="translate(205, 48)" font-size="12" fill="#0f172a">
              <circle cx="0" cy="0" r="5" fill="#3b82f6" />
              <text x="12" y="4" font-weight="600">Active ({active_count})</text>

              <circle cx="0" cy="24" r="5" fill="#64748b" />
              <text x="12" y="28">Drafted ({total_drafted})</text>

              <circle cx="0" cy="48" r="5" fill="#f59e0b" />
              <text x="12" y="52">Interview ({interview_count})</text>

              <circle cx="0" cy="72" r="5" fill="#8b5cf6" />
              <text x="12" y="76">Offer ({offer_count})</text>

              <circle cx="0" cy="96" r="5" fill="#ef4444" />
              <text x="12" y="100">Closed ({rejected_count})</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- Chart 2: By Sector Bar -->
      <div class="chart-card">
        <h3>Top Sectors</h3>
        <div class="chart-container">
          <svg width="450" height="230" viewBox="0 0 450 230" role="img" aria-label="By sector breakdown">
            <g transform="translate(10, 15)">
{sector_svg}
            </g>
          </svg>
        </div>
      </div>

      <!-- Chart 3: By Channel Bar -->
      <div class="chart-card">
        <h3>By Channel</h3>
        <div class="chart-container">
          <svg width="450" height="210" viewBox="0 0 450 210" role="img" aria-label="By channel: Online {channels['online']}, Portal {channels['portal']}">
            <g transform="translate(10, 15)">
              <text x="0" y="16" font-size="12" fill="#0f172a" font-weight="500">Online (Direct / Job Board)</text>
              <rect x="0" y="24" width="{min(280, channels['online'] * 45)}" height="20" rx="4" fill="#0284c7" />
              <text x="{min(280, channels['online'] * 45) + 10}" y="39" font-size="12" fill="#0f172a" font-weight="600">{channels['online']}</text>

              <text x="0" y="68" font-size="12" fill="#0f172a" font-weight="500">Portal / LinkedIn</text>
              <rect x="0" y="76" width="{min(280, channels['portal'] * 45)}" height="20" rx="4" fill="#38bdf8" />
              <text x="{min(280, channels['portal'] * 45) + 10}" y="91" font-size="12" fill="#0f172a" font-weight="600">{channels['portal']}</text>

              <text x="0" y="120" font-size="12" fill="#0f172a" font-weight="500">Referral</text>
              <rect x="0" y="128" width="2" height="20" rx="1" fill="#cbd5e1" />
              <text x="12" y="143" font-size="12" fill="#64748b" font-weight="500">{channels['referral']}</text>

              <text x="0" y="168" font-size="12" fill="#0f172a" font-weight="500">Other / Direct Email</text>
              <rect x="0" y="176" width="{max(2, channels['other'] * 45)}" height="20" rx="4" fill="#60a5fa" />
              <text x="{max(2, channels['other'] * 45) + 10}" y="191" font-size="12" fill="#0f172a" font-weight="600">{channels['other']}</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- Chart 4: Application Funnel -->
      <div class="chart-card">
        <h3>Application Funnel</h3>
        <div class="chart-container">
          <svg width="450" height="210" viewBox="0 0 450 210" role="img" aria-label="Funnel: Applied {total_sent}, Interview {interview_count}, Offer {offer_count}">
            <g transform="translate(10, 15)">
              <text x="0" y="16" font-size="12" fill="#0f172a" font-weight="500">Applied (Submitted)</text>
              <rect x="0" y="24" width="{max(2, total_sent * 80)}" height="18" rx="2" fill="#3b82f6" />
              <text x="{max(2, total_sent * 80) + 10}" y="38" font-size="11" fill="#0f172a" font-weight="600">{total_sent} (100%)</text>

              <text x="0" y="58" font-size="12" fill="#0f172a" font-weight="500">Interview</text>
              <rect x="0" y="66" width="{max(2, interview_count * 80)}" height="18" rx="2" fill="#f59e0b" />
              <text x="{max(2, interview_count * 80) + 10}" y="80" font-size="11" fill="#64748b">{interview_count} (0%)</text>

              <text x="0" y="100" font-size="12" fill="#0f172a" font-weight="500">Offer</text>
              <rect x="0" y="108" width="{max(2, offer_count * 80)}" height="18" rx="2" fill="#8b5cf6" />
              <text x="{max(2, offer_count * 80) + 10}" y="122" font-size="11" fill="#64748b">{offer_count} (0%)</text>

              <text x="0" y="142" font-size="12" fill="#0f172a" font-weight="500">Hired</text>
              <rect x="0" y="150" width="2" height="18" rx="2" fill="#cbd5e1" />
              <text x="12" y="164" font-size="11" fill="#64748b">0 (0%)</text>
            </g>
          </svg>
        </div>
      </div>
    </section>

    <!-- Table Section -->
    <section class="table-card">
      <div class="table-header">
        <h3>Applications</h3>
        <div class="filters-group">
          <input type="text" id="searchInput" class="filter-input" placeholder="🔍 Search company, role, sector...">
          <select id="statusFilter" class="filter-select">
            <option value="">All Statuses</option>
            <option value="drafted">Drafted</option>
            <option value="active">Active</option>
            <option value="interview">Interview</option>
            <option value="offer">Offer</option>
            <option value="hired">Hired</option>
            <option value="rejected">Rejected / Closed</option>
          </select>
          <select id="sectorFilter" class="filter-select">
            <option value="">All Sectors</option>
{sector_options}
          </select>
        </div>
      </div>

      <div class="table-wrapper">
        <table id="applicationsTable">
          <thead>
            <tr>
              <th>Date</th>
              <th>Deadline</th>
              <th>Company</th>
              <th>Role</th>
              <th>Sector</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Notes</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
{rows_html}
          </tbody>
        </table>
      </div>
    </section>

    <footer>
      Generated by Claude Code · ai-job-search · 2026-10-20
    </footer>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const searchInput = document.getElementById('searchInput');
      const statusFilter = document.getElementById('statusFilter');
      const sectorFilter = document.getElementById('sectorFilter');
      const table = document.getElementById('applicationsTable');
      const rows = table.querySelectorAll('tbody tr');

      function filterTable() {{
        const query = searchInput.value.toLowerCase().trim();
        const selectedStatus = statusFilter.value.toLowerCase().trim();
        const selectedSector = sectorFilter.value.toLowerCase().trim();

        rows.forEach(row => {{
          const text = row.textContent.toLowerCase();
          const rowStatus = (row.getAttribute('data-status') || '').toLowerCase();
          const rowSector = (row.getAttribute('data-sector') || '').toLowerCase();

          const matchesSearch = !query || text.includes(query);
          const matchesStatus = !selectedStatus || rowStatus === selectedStatus;
          const matchesSector = !selectedSector || rowSector === selectedSector;

          if (matchesSearch && matchesStatus && matchesSector) {{
            row.style.display = '';
          }} else {{
            row.style.display = 'none';
          }}
        }});
      }}

      searchInput.addEventListener('input', filterTable);
      statusFilter.addEventListener('change', filterTable);
      sectorFilter.addEventListener('change', filterTable);
    }});
  </script>
</body>
</html>
'''

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Generated dashboard: {out_path}")

if __name__ == '__main__':
    generate_dashboard()
