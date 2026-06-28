"""
count_commits.py — mahendra0011
NO author filter — counts ALL commits in repo across ALL branches.
Deduplicates by SHA.
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
    """
    Count ALL unique commit SHAs across ALL branches — NO author filter.
    Every commit in the repo is counted (deduplicated by SHA).
    """
    try:
        branches = pages(f"https://api.github.com/repos/{owner}/{repo_name}/branches")
    except Exception as e:
        print(f"    [!] branches error: {e}")
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
            except Exception as e:
                print(f"      branch '{br['name']}' error: {e}")
                break
    return len(shas)

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

def build_stats_block(total_commits, stars, prs, issues):
    return f"""<!-- STATS_START -->
<!-- Auto-updated by GitHub Action every day -->

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
        print("ERROR: markers not found!")
        return
    updated = re.sub(pattern, new_block.strip(), content, flags=re.DOTALL)
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("README.md patched ✅")

def main():
    print("=" * 55)
    print(f"  Counting ALL commits (no author filter)")
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
    print(f"  TOTAL: {total_commits:,} commits")
    print(f"{'='*55}\n")

    prs    = search_count(f"type:pr author:{USERNAME}")
    issues = search_count(f"type:issue author:{USERNAME}")

    block = build_stats_block(total_commits, stars, prs, issues)
    patch_readme(block)
    print(f"✅ Done! {total_commits:,} commits written to README")

if __name__ == "__main__":
    main()