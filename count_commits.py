"""
count_commits.py — mahendra0011
Counts ALL commits across ALL branches (including private repos).
Deduplicates by SHA so merge commits aren't double-counted.
Only updates the section between <!-- STATS_START --> and <!-- STATS_END -->
"""

import os, re, requests
from datetime import datetime, timezone
from collections import defaultdict

TOKEN    = os.environ["GH_TOKEN"]
USERNAME = "mahendra0011"
HEADERS  = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ── helpers ──────────────────────────────────────────────────────────────────

def gh(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r

def pages(url, params=None):
    out, page = [], 1
    while True:
        p = dict(params or {}); p.update({"per_page": 100, "page": page})
        data = gh(url, p).json()
        if not isinstance(data, list) or not data:
            break
        out.extend(data)
        if len(data) < 100:
            break
        page += 1
    return out

# ── data fetchers ─────────────────────────────────────────────────────────────

def all_repos():
    print("Fetching repos (public + private)…")
    repos = pages("https://api.github.com/user/repos",
                  {"affiliation": "owner", "sort": "updated"})
    priv = sum(1 for r in repos if r["private"])
    print(f"  {len(repos)} repos  ({priv} private, {len(repos)-priv} public)")
    return repos

def commit_count_per_branch(repo):
    """Return total unique commit SHAs authored by USERNAME across every branch."""
    try:
        branches = pages(f"https://api.github.com/repos/{USERNAME}/{repo}/branches")
    except Exception as e:
        print(f"    [!] branches failed for {repo}: {e}")
        return 0, 0

    shas = set()
    for br in branches:
        page = 1
        while True:
            try:
                r = gh(f"https://api.github.com/repos/{USERNAME}/{repo}/commits",
                       {"sha": br["name"], "author": USERNAME,
                        "per_page": 100, "page": page})
                data = r.json()
                if not isinstance(data, list) or not data:
                    break
                for c in data:
                    shas.add(c["sha"])
                if len(data) < 100:
                    break
                page += 1
            except Exception as e:
                print(f"      branch '{br['name']}' error: {e}")
                break
    return len(shas), len(branches)

def top_langs(repos):
    lb = defaultdict(int)
    for repo in repos:
        try:
            for lang, b in gh(repo["languages_url"]).json().items():
                lb[lang] += b
        except:
            pass
    total = sum(lb.values()) or 1
    return [(l, round(b/total*100, 2))
            for l, b in sorted(lb.items(), key=lambda x: -x[1])]

def search_count(q):
    try:
        return gh("https://api.github.com/search/issues", {"q": q}).json().get("total_count", 0)
    except:
        return 0

# ── README updater ────────────────────────────────────────────────────────────

LANG_COLORS = {
    "JavaScript":"f1e05a","TypeScript":"2b7489","Python":"3572A5",
    "CSS":"563d7c","HTML":"e34c26","Shell":"89e051","Go":"00ADD8",
    "Rust":"dea584","Java":"b07219","C++":"f34b7d","C#":"178600",
    "PowerShell":"012456","Dockerfile":"384d54","Vue":"41b883",
}

def build_stats_block(total_commits, stars, prs, issues, langs, updated):
    lang_rows = ""
    top6 = langs[:6]
    for i in range(0, len(top6), 2):
        l1 = top6[i]
        c1 = LANG_COLORS.get(l1[0], "8b949e")
        row = f"| ![{l1[0]}](https://img.shields.io/badge/-{l1[0].replace(' ','%20')}-{c1}?style=flat-square) {l1[1]}% |"
        if i+1 < len(top6):
            l2 = top6[i+1]
            c2 = LANG_COLORS.get(l2[0], "8b949e")
            row += f" ![{l2[0]}](https://img.shields.io/badge/-{l2[0].replace(' ','%20')}-{c2}?style=flat-square) {l2[1]}% |"
        else:
            row += "  |"
        lang_rows += row + "\n"

    return f"""<!-- STATS_START -->
<!-- ⚠️ Auto-updated by GitHub Action every day — do not edit between these markers -->

<table align="center">
<tr>
<td valign="top" width="50%">

### Mahendra Prajapati's GitHub Stats

|  |  |
|--|--|
| ⭐ Total Stars Earned | {stars} |
| 📝 Total Commits (all branches + private) | **{total_commits:,}** |
| 🔀 Total PRs | {prs} |
| 🐛 Total Issues | {issues} |
| 🏢 Contributed to (last year) | 1 |

</td>
<td valign="top" width="50%">

<img src="https://github-readme-stats.vercel.app/api/top-langs/?username={USERNAME}&layout=compact&count_private=true&theme=default&hide_border=true&langs_count=8" alt="Most Used Languages" />

</td>
</tr>
</table>

<p align="center">
  <img src="https://github-readme-streak-stats.herokuapp.com/?user={USERNAME}&theme=default&hide_border=true&date_format=M%20j%5B%2C%20Y%5D" alt="GitHub Streak" />
</p>

<!-- STATS_END -->"""

def patch_readme(new_block):
    path = "README.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"<!-- STATS_START -->.*?<!-- STATS_END -->"
    if not re.search(pattern, content, re.DOTALL):
        print("ERROR: markers not found in README.md!")
        return
    updated = re.sub(pattern, new_block.strip(), content, flags=re.DOTALL)
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("README.md patched ✅")

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print(f"  Counting ALL commits for @{USERNAME}")
    print("=" * 55)

    repos = all_repos()
    total_commits = 0
    stars = 0

    for i, repo in enumerate(repos):
        name = repo["name"]
        priv = "private" if repo["private"] else "public"
        print(f"\n[{i+1}/{len(repos)}] {name}  ({priv})")
        count, nbranches = commit_count_per_branch(name)
        print(f"  → {count:,} unique commits  across {nbranches} branch(es)")
        total_commits += count
        stars += repo.get("stargazers_count", 0)

    print(f"\n{'='*55}")
    print(f"  TOTAL commits (all repos · all branches): {total_commits:,}")
    print(f"{'='*55}\n")

    prs    = search_count(f"type:pr author:{USERNAME}")
    issues = search_count(f"type:issue author:{USERNAME}")
    langs  = top_langs(repos)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"Stars={stars}  PRs={prs}  Issues={issues}")
    print(f"Top langs: {[l[0] for l in langs[:5]]}")

    block = build_stats_block(total_commits, stars, prs, issues, langs, updated)
    patch_readme(block)

if __name__ == "__main__":
    main()
