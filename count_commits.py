"""
count_commits.py — mahendra0011
Counts ALL commits across ALL branches (no author filter).
Updates README with animated SVG stats block.
"""

import os, re, requests
from collections import defaultdict

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
    """
    Fetch TOTAL contributions (commits + PRs + issues + reviews) via GraphQL.
    This is the same number shown on the GitHub profile contribution graph.
    We sum ALL contribution years to get lifetime total.
    """
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalPullRequestReviewContributions
          restrictedContributionsCount
        }
      }
    }
    """
    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"login": USERNAME}},
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=30
        )
        data = r.json()
        user = data["data"]["user"]
        cc = user["contributionsCollection"]
        # totalContributions from calendar = all contribution types combined (this year)
        calendar_total = cc["contributionCalendar"]["totalContributions"]
        print(f"  Contributions this year (calendar): {calendar_total:,}")
        return calendar_total
    except Exception as e:
        print(f"  GraphQL error: {e}")
        return 0

def all_repos():
    print("Fetching ALL repos...")
    repos = pages("https://api.github.com/user/repos", {
        "affiliation": "owner,collaborator,organization_member",
        "sort": "updated",
        "visibility": "all"
    })
    seen, all_r = set(), []
    for r in repos:
        if r["id"] not in seen:
            seen.add(r["id"])
            all_r.append(r)
    priv = sum(1 for r in all_r if r["private"])
    print(f"  {len(all_r)} repos ({priv} private)")
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
                r = gh(
                    f"https://api.github.com/repos/{owner}/{repo_name}/commits",
                    {"sha": br["name"], "per_page": 100, "page": page}
                )
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

def build_stats_block(total_commits, contributions, stars, prs, issues):
    """
    Builds an animated SVG stats section for the README.
    No external badge services needed for the stats table.
    The streak + top-langs cards still use their respective services.
    """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="860" height="220" viewBox="0 0 860 220">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0d1117"/>
      <stop offset="100%" style="stop-color:#161b22"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#36bcf7"/>
      <stop offset="100%" style="stop-color:#a855f7"/>
    </linearGradient>
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1c2128;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#161b22;stop-opacity:1"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}
      @keyframes countUp {{
        from {{ opacity: 0; }}
        to   {{ opacity: 1; }}
      }}
      @keyframes barGrow {{
        from {{ width: 0; }}
      }}
      @keyframes pulse {{
        0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.6; }}
      }}
      .card  {{ animation: fadeUp .6s ease both; }}
      .c1    {{ animation-delay: 0.0s; }}
      .c2    {{ animation-delay: 0.15s; }}
      .c3    {{ animation-delay: 0.30s; }}
      .c4    {{ animation-delay: 0.45s; }}
      .c5    {{ animation-delay: 0.60s; }}
      .num   {{ animation: countUp .8s ease both; }}
      .dot   {{ animation: pulse 2s ease-in-out infinite; }}
    </style>
  </defs>

  <!-- Background -->
  <rect width="860" height="220" rx="14" fill="url(#bg)" stroke="#30363d" stroke-width="1"/>

  <!-- Top accent bar -->
  <rect width="860" height="3" rx="2" fill="url(#accent)"/>

  <!-- Title -->
  <text x="430" y="34" text-anchor="middle" font-family="Segoe UI,sans-serif"
        font-size="15" font-weight="700" fill="#e6edf3" filter="url(#glow)">
    ✦ Mahendra Prajapati · GitHub Stats ✦
  </text>
  <!-- Live dot -->
  <circle cx="808" cy="28" r="5" fill="#3fb950" class="dot"/>
  <text x="817" y="33" font-family="Segoe UI,sans-serif" font-size="10" fill="#3fb950">Live</text>

  <!-- ── CARD 1: Total Commits ── -->
  <g class="card c1" transform="translate(20,52)">
    <rect width="152" height="108" rx="10" fill="url(#cardBg)" stroke="#30363d" stroke-width="1"/>
    <rect width="152" height="3" rx="2" fill="#36bcf7" opacity=".8"/>
    <text x="76" y="30" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="11" fill="#8b949e">🕐 Total Commits</text>
    <text x="76" y="68" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="30" font-weight="800" fill="#36bcf7" class="num" filter="url(#glow)">{total_commits:,}</text>
    <text x="76" y="92" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="10" fill="#484f58">all branches · all repos</text>
  </g>

  <!-- ── CARD 2: Contributions ── -->
  <g class="card c2" transform="translate(188,52)">
    <rect width="152" height="108" rx="10" fill="url(#cardBg)" stroke="#30363d" stroke-width="1"/>
    <rect width="152" height="3" rx="2" fill="#a855f7" opacity=".8"/>
    <text x="76" y="30" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="11" fill="#8b949e">⚡ Contributions</text>
    <text x="76" y="68" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="30" font-weight="800" fill="#a855f7" class="num" filter="url(#glow)">{contributions:,}</text>
    <text x="76" y="92" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="10" fill="#484f58">this year · calendar</text>
  </g>

  <!-- ── CARD 3: PRs ── -->
  <g class="card c3" transform="translate(356,52)">
    <rect width="152" height="108" rx="10" fill="url(#cardBg)" stroke="#30363d" stroke-width="1"/>
    <rect width="152" height="3" rx="2" fill="#3fb950" opacity=".8"/>
    <text x="76" y="30" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="11" fill="#8b949e">⑂ Pull Requests</text>
    <text x="76" y="68" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="30" font-weight="800" fill="#3fb950" class="num" filter="url(#glow)">{prs}</text>
    <text x="76" y="92" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="10" fill="#484f58">merged &amp; open</text>
  </g>

  <!-- ── CARD 4: Stars ── -->
  <g class="card c4" transform="translate(524,52)">
    <rect width="152" height="108" rx="10" fill="url(#cardBg)" stroke="#30363d" stroke-width="1"/>
    <rect width="152" height="3" rx="2" fill="#f0b429" opacity=".8"/>
    <text x="76" y="30" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="11" fill="#8b949e">☆ Stars Earned</text>
    <text x="76" y="68" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="30" font-weight="800" fill="#f0b429" class="num" filter="url(#glow)">{stars}</text>
    <text x="76" y="92" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="10" fill="#484f58">across all repos</text>
  </g>

  <!-- ── CARD 5: Issues ── -->
  <g class="card c5" transform="translate(692,52)">
    <rect width="152" height="108" rx="10" fill="url(#cardBg)" stroke="#30363d" stroke-width="1"/>
    <rect width="152" height="3" rx="2" fill="#f85149" opacity=".8"/>
    <text x="76" y="30" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="11" fill="#8b949e">⊙ Issues</text>
    <text x="76" y="68" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="30" font-weight="800" fill="#f85149" class="num" filter="url(#glow)">{issues}</text>
    <text x="76" y="92" text-anchor="middle" font-family="Segoe UI,sans-serif"
          font-size="10" fill="#484f58">opened by me</text>
  </g>

  <!-- Bottom bar: skill bar visual -->
  <text x="20" y="186" font-family="Segoe UI,sans-serif" font-size="10" fill="#484f58">JavaScript</text>
  <rect x="20" y="191" width="730" height="4" rx="2" fill="#21262d"/>
  <rect x="20" y="191" width="679" height="4" rx="2" fill="url(#accent)" style="animation:barGrow 1.2s ease both"/>
  <text x="758" y="197" font-family="Segoe UI,sans-serif" font-size="10" fill="#36bcf7">93%</text>

  <!-- Footer -->
  <text x="430" y="216" text-anchor="middle" font-family="Segoe UI,sans-serif"
        font-size="9" fill="#30363d">Auto-updated daily via GitHub Actions</text>
</svg>"""

    return f"""<!-- STATS_START -->
<!-- Auto-updated by GitHub Action every day — do not edit between these markers -->

<p align="center">
<img src="https://raw.githubusercontent.com/{USERNAME}/{USERNAME}/main/stats.svg" alt="GitHub Stats" />
</p>

<p align="center">
<img src="https://github-readme-streak-stats.herokuapp.com/?user={USERNAME}&hide_border=true&date_format=M%20j%5B%2C%20Y%5D&theme=tokyonight_duo" alt="GitHub Streak" />
&nbsp;&nbsp;
<img src="https://github-readme-stats.vercel.app/api/top-langs/?username={USERNAME}&layout=compact&count_private=true&hide_border=true&langs_count=8&theme=tokyonight" alt="Top Languages" />
</p>

<!-- STATS_END -->""", svg

def patch_readme(new_block):
    path = "README.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"<!-- STATS_START -->.*?<!-- STATS_END -->"
    if not re.search(pattern, content, re.DOTALL):
        print("ERROR: markers not found in README!")
        return
    updated = re.sub(pattern, new_block.strip(), content, flags=re.DOTALL)
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("README.md patched ✅")

def write_svg(svg_content):
    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("stats.svg written ✅")

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

    # ✅ FIXED: Proper GraphQL-based contribution count
    contributions = get_contributions()
    print(f"  Total Contributions (calendar): {contributions:,}")

    prs    = search_count(f"type:pr author:{USERNAME}")
    issues = search_count(f"type:issue author:{USERNAME}")

    readme_block, svg_content = build_stats_block(total_commits, contributions, stars, prs, issues)

    # Write animated SVG file (committed alongside README)
    write_svg(svg_content)

    # Patch the README to point to the SVG
    patch_readme(readme_block)

    print(f"\n✅ Done!")
    print(f"   Commits: {total_commits:,} | Contributions: {contributions:,} | Stars: {stars} | PRs: {prs} | Issues: {issues}")

if __name__ == "__main__":
    main()