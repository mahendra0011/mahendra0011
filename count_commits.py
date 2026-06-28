"""
count_commits.py — mahendra0011
Counts ALL commits across ALL branches (no author filter).
Updates README with github-readme-stats cards (exact screenshot UI).
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
          contributionCalendar {
            totalContributions
          }
          restrictedContributionsCount
        }
      }
    }
    """
    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json={"query": """
                query($login: String!) {
                  user(login: $login) { createdAt }
                }
            """, "variables": {"login": USERNAME}},
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=30
        )
        created_at = r.json()["data"]["user"]["createdAt"]
        join_year = int(created_at[:4])
    except:
        join_year = 2019

    current_year = datetime.now().year
    total = 0

    print(f"  Fetching contributions from {join_year} to {current_year}...")

    for year in range(join_year, current_year + 1):
        try:
            r = requests.post(
                "https://api.github.com/graphql",
                json={"query": query, "variables": {
                    "login": USERNAME,
                    "from": f"{year}-01-01T00:00:00Z",
                    "to":   f"{year}-12-31T23:59:59Z"
                }},
                headers={"Authorization": f"Bearer {TOKEN}"},
                timeout=30
            )
            data = r.json()["data"]["user"]["contributionsCollection"]
            calendar   = data["contributionCalendar"]["totalContributions"]
            restricted = data["restrictedContributionsCount"]
            year_total = calendar + restricted
            print(f"    {year}: {calendar} public + {restricted} private = {year_total}")
            total += year_total
        except Exception as e:
            print(f"    {year}: error - {e}")

    return total

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
    return [(l, round(b/total*100, 2))
            for l, b in sorted(lb.items(), key=lambda x: -x[1])]

def build_stats_block(total_commits, stars, prs, issues):
    return f"""<!-- STATS_START -->
<!-- Auto-updated by GitHub Action every day — do not edit between these markers -->

<table align="center" width="100%" border="1" cellpadding="10" cellspacing="0" style="border-collapse:collapse">
<tr>
<td valign="top" width="50%">

**Mahendra Prajapati 's GitHub Stats**

<table>
<tr><td>☆ <b>Total Stars Earned:</b></td><td>{stars}</td></tr>
<tr><td>🕐 <b>Total Commits:</b></td><td><b>{total_commits:,}</b></td></tr>
<tr><td>⑂ <b>Total PRs:</b></td><td>{prs}</td></tr>
<tr><td>⊙ <b>Total Issues:</b></td><td>{issues}</td></tr>
<tr><td>⊟ <b>Contributed to (last year):</b></td><td>{total_commits:,}</td></tr>
</table>

</td>
<td valign="top" width="50%" align="center">

<img src="https://github-readme-stats.vercel.app/api/top-langs/?username={USERNAME}&layout=compact&count_private=true&hide_border=true&langs_count=8" alt="Most Used Languages" />

</td>
</tr>
</table>

<br/>

<p align="center">
<img src="https://github-readme-streak-stats.herokuapp.com/?user={USERNAME}&hide_border=true&date_format=M%20j%5B%2C%20Y%5D" alt="GitHub Streak Stats" />
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
    print(f"  Total Contributions (all years): {contributions:,}")

    prs    = search_count(f"type:pr author:{USERNAME}")
    issues = search_count(f"type:issue author:{USERNAME}")

    block = build_stats_block(total_commits, stars, prs, issues)
    patch_readme(block)
    print(f"✅ Done! Commits: {total_commits:,} | Contributions: {contributions:,}")

if __name__ == "__main__":
    main()