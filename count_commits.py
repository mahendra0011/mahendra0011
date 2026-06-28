"""
count_commits.py — mahendra0011
Counts ALL commits across ALL branches (no author filter).
Generates stats.svg and updates README.
"""

import os, re, requests
from collections import defaultdict
from datetime import datetime

TOKEN    = os.environ["GH_TOKEN"]
USERNAME = "mahendra0011"
HEADERS  = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def gh(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r

def pages(url, params=None):
    out, page = [], 1
    while True:
        p = dict(params or {})
        p.update({"per_page": 100, "page": page})
        try:
            data = gh(url, p).json()
        except:
            break
        if not isinstance(data, list) or not data:
            break
        out.extend(data)
        if len(data) < 100:
            break
        page += 1
    return out

def get_contributions():
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
          restrictedContributionsCount
        }
      }
    }
    """
    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json={"query": "query($login:String!){user(login:$login){createdAt}}", "variables": {"login": USERNAME}},
            headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30
        )
        join_year = int(r.json()["data"]["user"]["createdAt"][:4])
    except:
        join_year = 2019

    current_year = datetime.now().year
    total = 0
    print(f"  Fetching contributions {join_year} to {current_year}...")
    for year in range(join_year, current_year + 1):
        try:
            r = requests.post(
                "https://api.github.com/graphql",
                json={"query": query, "variables": {
                    "login": USERNAME,
                    "from": f"{year}-01-01T00:00:00Z",
                    "to":   f"{year}-12-31T23:59:59Z"
                }},
                headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30
            )
            data = r.json()["data"]["user"]["contributionsCollection"]
            cal  = data["contributionCalendar"]["totalContributions"]
            priv = data["restrictedContributionsCount"]
            print(f"    {year}: {cal} + {priv} private = {cal+priv}")
            total += cal + priv
        except Exception as e:
            print(f"    {year}: error - {e}")
    return total

def get_streak_data():
    """Fetch streak info via GraphQL contribution weeks"""
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"login": USERNAME}},
            headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30
        )
        data = r.json()["data"]["user"]
        created_at = data["createdAt"]
        weeks = data["contributionsCollection"]["contributionCalendar"]["weeks"]

        days = []
        for week in weeks:
            for day in week["contributionDays"]:
                days.append((day["date"], day["contributionCount"]))

        days.sort(key=lambda x: x[0])
        today_str = datetime.now().strftime("%Y-%m-%d")
        days = [d for d in days if d[0] <= today_str]

        # Current streak
        current = 0
        current_start = ""
        current_end = ""
        for date, count in reversed(days):
            if count > 0:
                current += 1
                current_end = current_end or date
                current_start = date
            else:
                break

        # Longest streak
        longest = 0
        longest_start = ""
        longest_end = ""
        run = 0
        run_start = ""
        for date, count in days:
            if count > 0:
                run += 1
                if run == 1:
                    run_start = date
                if run > longest:
                    longest = run
                    longest_start = run_start
                    longest_end = date
            else:
                run = 0
                run_start = ""

        def fmt(d):
            if not d:
                return ""
            dt = datetime.strptime(d, "%Y-%m-%d")
            return dt.strftime("%b %-d")

        # Account start
        acc = datetime.strptime(created_at[:10], "%Y-%m-%d")
        acc_str = acc.strftime("%b %-d, %Y")

        return {
            "current": current,
            "current_start": fmt(current_start),
            "current_end": fmt(current_end),
            "longest": longest,
            "longest_start": fmt(longest_start),
            "longest_end": fmt(longest_end),
            "account_start": acc_str,
        }
    except Exception as e:
        print(f"  Streak error: {e}")
        return {
            "current": 0, "current_start": "", "current_end": "",
            "longest": 0, "longest_start": "", "longest_end": "",
            "account_start": "2024",
        }

def get_top_langs(repos):
    lb = defaultdict(int)
    for repo in repos:
        try:
            for lang, b in gh(repo["languages_url"]).json().items():
                lb[lang] += b
        except:
            pass
    total = sum(lb.values()) or 1
    return [(l, round(b/total*100, 2)) for l, b in sorted(lb.items(), key=lambda x: -x[1])[:8]]

LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572A5",
    "CSS": "#563d7c", "HTML": "#e34c26", "Shell": "#89e051",
    "PowerShell": "#89e051", "Dockerfile": "#384d54", "Go": "#00ADD8",
    "Rust": "#dea584", "Java": "#b07219", "C++": "#f34b7d",
    "C": "#555555", "Ruby": "#701516", "PHP": "#4F5D95",
    "Vue": "#41b883", "Swift": "#F05138", "Kotlin": "#A97BFF",
}

def generate_svg(total_commits, stars, prs, issues, total_contributions, streak, langs):
    cs  = streak["current"]
    ls  = streak["longest"]
    cs_start = streak["current_start"]
    cs_end   = streak["current_end"]
    ls_start = streak["longest_start"]
    ls_end   = streak["longest_end"]
    acc_start = streak["account_start"]

    # Build lang bar segments
    bar_x = 468
    bar_w = 380
    bar_segments = ""
    cx = bar_x
    for lang, pct in langs:
        w = round(bar_w * pct / 100)
        if w < 1:
            continue
        color = LANG_COLORS.get(lang, "#ccc")
        bar_segments += f'<rect x="{cx}" y="48" width="{w}" height="10" fill="{color}"/>\n'
        cx += w

    # Build lang list (2 columns)
    lang_items = ""
    col1 = langs[:4]
    col2 = langs[4:8]
    for i, (lang, pct) in enumerate(col1):
        y = 80 + i * 25
        color = LANG_COLORS.get(lang, "#ccc")
        lang_items += f'<circle cx="476" cy="{y-4}" r="5" fill="{color}"/>\n'
        lang_items += f'<text x="486" y="{y}" class="lang-name">{lang}</text>\n'
        lang_items += f'<text x="580" y="{y}" class="lang-pct">{pct}%</text>\n'
    for i, (lang, pct) in enumerate(col2):
        y = 80 + i * 25
        color = LANG_COLORS.get(lang, "#ccc")
        lang_items += f'<circle cx="660" cy="{y-4}" r="5" fill="{color}"/>\n'
        lang_items += f'<text x="670" y="{y}" class="lang-name">{lang}</text>\n'
        lang_items += f'<text x="770" y="{y}" class="lang-pct">{pct}%</text>\n'

    streak_date_line = f"{cs_start} - {cs_end}" if cs_start else "—"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="430" viewBox="0 0 900 430">
  <defs>
    <style>
      .title      {{ font: 600 15px 'Segoe UI',sans-serif; fill: #1f6feb; }}
      .label      {{ font: 400 12px 'Segoe UI',sans-serif; fill: #24292f; }}
      .value-blue {{ font: 700 12px 'Segoe UI',sans-serif; fill: #1f6feb; }}
      .value-bold {{ font: 700 12px 'Segoe UI',sans-serif; fill: #24292f; }}
      .sec-title  {{ font: 600 15px 'Segoe UI',sans-serif; fill: #1f6feb; }}
      .lang-name  {{ font: 400 11px 'Segoe UI',sans-serif; fill: #24292f; }}
      .lang-pct   {{ font: 400 11px 'Segoe UI',sans-serif; fill: #57606a; }}
      .st-big     {{ font: 700 32px 'Segoe UI',sans-serif; fill: #24292f; }}
      .st-label   {{ font: 400 13px 'Segoe UI',sans-serif; fill: #57606a; }}
      .st-date    {{ font: 400 11px 'Segoe UI',sans-serif; fill: #57606a; }}
      .st-cur     {{ font: 700 13px 'Segoe UI',sans-serif; fill: #fb8f44; }}
    </style>
  </defs>

  <rect width="900" height="430" fill="white"/>

  <!-- Stats card -->
  <rect x="10" y="10" width="420" height="195" rx="6" fill="white" stroke="#d0d7de" stroke-width="1"/>
  <text x="28" y="38" class="title">Mahendra Prajapati 's GitHub Stats</text>

  <text x="28" y="66"  class="label">☆  Total Stars Earned:</text>
  <text x="245" y="66"  class="value-blue">{stars}</text>

  <text x="28" y="93"  class="label">🕐  Total Commits:</text>
  <text x="245" y="93"  class="value-bold">{total_commits:,}</text>

  <text x="28" y="120" class="label">⑂  Total PRs:</text>
  <text x="245" y="120" class="value-blue">{prs}</text>

  <text x="28" y="147" class="label">⊙  Total Issues:</text>
  <text x="245" y="147" class="value-blue">{issues}</text>

  <text x="28" y="174" class="label">⊟  Contributed to (last year):</text>
  <text x="245" y="174" class="value-blue">{total_commits:,}</text>

  <!-- Rank circle -->
  <circle cx="372" cy="112" r="40" fill="none" stroke="#e6edf3" stroke-width="5"/>
  <circle cx="372" cy="112" r="40" fill="none" stroke="#1f6feb" stroke-width="5"
          stroke-dasharray="22 230" stroke-linecap="round"
          transform="rotate(-90 372 112)"/>
  <text x="372" y="118" text-anchor="middle" font-family="Segoe UI,sans-serif" font-size="15" font-weight="700" fill="#57606a">C</text>

  <!-- Languages card -->
  <rect x="445" y="10" width="445" height="195" rx="6" fill="white" stroke="#d0d7de" stroke-width="1"/>
  <text x="463" y="38" class="sec-title">Most Used Languages</text>

  <!-- Bar background -->
  <rect x="468" y="48" width="380" height="10" rx="5" fill="#eaeef2"/>
  {bar_segments}

  {lang_items}

  <!-- Streak card -->
  <rect x="10" y="225" width="880" height="195" rx="6" fill="white" stroke="#d0d7de" stroke-width="1"/>
  <line x1="303" y1="255" x2="303" y2="400" stroke="#d0d7de" stroke-width="1"/>
  <line x1="597" y1="255" x2="597" y2="400" stroke="#d0d7de" stroke-width="1"/>

  <!-- Total Contributions -->
  <text x="151" y="315" text-anchor="middle" class="st-big">{total_contributions:,}</text>
  <text x="151" y="343" text-anchor="middle" class="st-label">Total Contributions</text>
  <text x="151" y="362" text-anchor="middle" class="st-date">{acc_start} - Present</text>

  <!-- Current Streak -->
  <circle cx="450" cy="308" r="44" fill="none" stroke="#fb8f44" stroke-width="5"/>
  <text x="450" y="274" text-anchor="middle" font-family="Segoe UI,sans-serif" font-size="20" fill="#fb8f44">🔥</text>
  <text x="450" y="320" text-anchor="middle" font-family="Segoe UI,sans-serif" font-size="28" font-weight="700" fill="#fb8f44">{cs}</text>
  <text x="450" y="366" text-anchor="middle" class="st-cur">Current Streak</text>
  <text x="450" y="384" text-anchor="middle" class="st-date">{streak_date_line}</text>

  <!-- Longest Streak -->
  <text x="749" y="315" text-anchor="middle" class="st-big">{ls}</text>
  <text x="749" y="343" text-anchor="middle" class="st-label">Longest Streak</text>
  <text x="749" y="362" text-anchor="middle" class="st-date">{ls_start} - {ls_end}</text>

</svg>"""
    return svg

def all_repos():
    print("Fetching ALL repos...")
    repos = pages("https://api.github.com/user/repos", {
        "affiliation": "owner,collaborator,organization_member",
        "sort": "updated", "visibility": "all"
    })
    seen, all_r = set(), []
    for r in repos:
        if r["id"] not in seen:
            seen.add(r["id"])
            all_r.append(r)
    print(f"  {len(all_r)} repos")
    return all_r

def count_commits_in_repo(owner, repo_name):
    try:
        branches = pages(f"https://api.github.com/repos/{owner}/{repo_name}/branches")
    except:
        return 0
    shas = set()
    for br in branches:
        page = 1
        while True:
            try:
                r = gh(f"https://api.github.com/repos/{owner}/{repo_name}/commits",
                       {"sha": br["name"], "per_page": 100, "page": page})
                data = r.json()
                if not isinstance(data, list) or not data:
                    break
                for c in data:
                    shas.add(c["sha"])
                if len(data) < 100:
                    break
                page += 1
            except:
                break
    return len(shas)

def search_count(q):
    try:
        return gh("https://api.github.com/search/issues", {"q": q}).json().get("total_count", 0)
    except:
        return 0

def build_stats_block():
    return """<!-- STATS_START -->
<!-- Auto-updated by GitHub Action every day — do not edit between these markers -->

<p align="center">
  <img src="stats.svg" alt="GitHub Stats" width="900"/>
</p>

<!-- STATS_END -->"""

def patch_readme(new_block):
    path = "README.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"<!-- STATS_START -->.*?<!-- STATS_END -->"
    if not re.search(pattern, content, re.DOTALL):
        print("ERROR: markers not found!")
        return
    updated = re.sub(pattern, new_block.strip(), content, flags=re.DOTALL)
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("README.md patched ✅")

def main():
    print("=" * 55)
    print(f"  Counting ALL commits for @{USERNAME}")
    print("=" * 55)

    repos = all_repos()
    total_commits = 0
    stars = 0

    for i, repo in enumerate(repos):
        owner = repo["owner"]["login"]
        name  = repo["name"]
        priv  = "private" if repo["private"] else "public"
        print(f"\n[{i+1}/{len(repos)}] {owner}/{name} ({priv})")
        count = count_commits_in_repo(owner, name)
        print(f"  → {count:,} commits")
        total_commits += count
        stars += repo.get("stargazers_count", 0)

    print(f"\n{'='*55}")
    print(f"  TOTAL commits: {total_commits:,}")
    print(f"{'='*55}\n")

    contributions = get_contributions()
    streak        = get_streak_data()
    langs         = get_top_langs(repos)

    prs    = search_count(f"type:pr author:{USERNAME}")
    issues = search_count(f"type:issue author:{USERNAME}")

    svg = generate_svg(total_commits, stars, prs, issues, total_commits, streak, langs)
    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("stats.svg written ✅")

    patch_readme(build_stats_block())
    print(f"✅ Done! Commits: {total_commits:,} | Contributions: {contributions:,}")

if __name__ == "__main__":
    main()