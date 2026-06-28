"""
count_commits.py — mahendra0011
Counts ALL commits across ALL branches (no author filter).
Updates README with github-readme-stats cards (exact screenshot UI).
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
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
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
        return r.json()["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except:
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

def top_langs(repos):
    lb = defaultdict(int)
    for repo in repos:
        try:
            for lang, b in gh(repo["languages_url"]).json().items():
                lb[lang] += b
        except:
            pass
    total = sum(lb.values()) or 1
    return [(l, round(b / total * 100, 2))
            for l, b in sorted(lb.items(), key=lambda x: -x[1])]

def build_stats_block(total_commits, contributions, stars, prs, issues):
    return f"""<!-- STATS_START -->
<!-- Auto-updated by GitHub Action every day — do not edit between these markers -->

<table align="center" width="100%">
<tr>
<td valign="top" width="48%">

**Mahendra Prajapati's GitHub Stats**

| | |
|---|---|
| ⭐ Total Stars Earned: | {stars} |
| 🕐 Total Commits (all branches): | **{total_commits:,}** |
| 🔀 Total PRs: | {prs} |
| 🐛 Total Issues: | {issues} |
| 🏢 Contributed to (last year): | 1 |

</td>
<td valign="top" width="52%">

**Most Used Languages**

| | |
|---|---|
| <img src='https://img.shields.io/badge/-JavaScript-f1e05a?style=flat-square' height='14'> **JavaScript** 90.26% | <img src='https://img.shields.io/badge/-TypeScript-2b7489?style=flat-square' height='14'> **TypeScript** 5.56% |
| <img src='https://img.shields.io/badge/-CSS-563d7c?style=flat-square' height='14'> **CSS** 3.55% | <img src='https://img.shields.io/badge/-HTML-e34c26?style=flat-square' height='14'> **HTML** 0.44% |
| <img src='https://img.shields.io/badge/-Python-3572A5?style=flat-square' height='14'> **Python** 0.15% | <img src='https://img.shields.io/badge/-PowerShell-012456?style=flat-square' height='14'> **PowerShell** 0.03% |

</td>
</tr>
</table>

<br>

<table align="center" width="100%">
<tr>
<td align="center" width="33%">

### {contributions:,}
**Total Contributions**
<sub>Nov 6, 2024 - Present</sub>

</td>
<td align="center" width="34%">

<img src="https://github-readme-streak-stats.herokuapp.com/?user={USERNAME}&theme=default&hide_border=true&date_format=M%20j%5B%2C%20Y%5D" alt="GitHub Streak" width="280"/>

</td>
<td align="center" width="33%">

### 23
**Longest Streak**
<sub>May 18 - Jun 9</sub>

</td>
</tr>
</table>

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
    print(f"  TOTAL commits : {total_commits:,}")
    print(f"  TOTAL stars   : {stars:,}")
    print(f"{'='*55}\n")

    contributions = get_contributions()
    print(f"  Total Contributions: {contributions:,}")

    prs    = search_count(f"type:pr author:{USERNAME}")
    issues = search_count(f"type:issue author:{USERNAME}")

    block = build_stats_block(total_commits, contributions, stars, prs, issues)
    patch_readme(block)
    print(f"✅ Done! Commits: {total_commits:,} | Contributions: {contributions:,}")

if __name__ == "__main__":
    main()