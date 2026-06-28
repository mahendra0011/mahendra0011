"""
count_commits.py — mahendra0011
Counts EVERY SINGLE commit:
- owner repos + collaborator repos + org repos
- ALL branches (feature, dev, main, merge wali sab)
- Private repos bhi
- Deduplication by SHA (merge commits double count nahi honge)
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
    print("Fetching ALL repos (owner + collaborator + org)...")
    
    # 1. Owner repos
    owner_repos = pages("https://api.github.com/user/repos", {
        "affiliation": "owner",
        "sort": "updated",
        "visibility": "all"
    })
    print(f"  Owner repos: {len(owner_repos)}")
    
    # 2. Collaborator repos (jahan contribute kiya)
    collab_repos = pages("https://api.github.com/user/repos", {
        "affiliation": "collaborator",
        "sort": "updated",
        "visibility": "all"
    })
    print(f"  Collaborator repos: {len(collab_repos)}")
    
    # 3. Org member repos
    org_repos = pages("https://api.github.com/user/repos", {
        "affiliation": "organization_member",
        "sort": "updated",
        "visibility": "all"
    })
    print(f"  Org repos: {len(org_repos)}")

    # Deduplicate by repo id
    seen = set()
    all_r = []
    for r in owner_repos + collab_repos + org_repos:
        if r["id"] not in seen:
            seen.add(r["id"])
            all_r.append(r)
    
    priv = sum(1 for r in all_r if r["private"])
    print(f"\n  TOTAL unique repos: {len(all_r)} ({priv} private, {len(all_r)-priv} public)")
    return all_r

def count_commits_in_repo(owner, repo_name):
    """
    Count ALL unique commits by USERNAME across ALL branches.
    Uses SHA deduplication — merge commits not double counted.
    Also tries without author filter to catch commits with different email.
    """
    try:
        branches = pages(f"https://api.github.com/repos/{owner}/{repo_name}/branches")
    except Exception as e:
        print(f"    [!] branches failed: {e}")
        return 0

    shas = set()

    for br in branches:
        # Try with author filter
        for author_filter in [USERNAME, None]:
            page = 1
            while True:
                try:
                    params = {
                        "sha": br["name"],
                        "per_page": 100,
                        "page": page
                    }
                    if author_filter:
                        params["author"] = author_filter

                    r = gh(
                        f"https://api.github.com/repos/{owner}/{repo_name}/commits",
                        params
                    )
                    data = r.json()
                    if not isinstance(data, list) or not data:
                        break

                    if author_filter is None:
                        # Filter manually — check author login
                        for c in data:
                            try:
                                if c.get("author") and c["author"].get("login") == USERNAME:
                                    shas.add(c["sha"])
                            except:
                                pass
                    else:
                        for c in data:
                            shas.add(c["sha"])

                    if len(data) < 100:
                        break
                    page += 1
                except Exception as e:
                    break

            # Only do the unfiltered pass once (for first branch it's enough to check)
            if author_filter is None:
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

LANG_COLORS = {
    "JavaScript":"f1e05a","TypeScript":"2b7489","Python":"3572A5",
    "CSS":"563d7c","HTML":"e34c26","Shell":"89e051","Go":"00ADD8",
    "Rust":"dea584","Java":"b07219","C++":"f34b7d","C#":"178600",
    "PowerShell":"012456","Dockerfile":"384d54","Vue":"41b883",
}

def build_stats_block(total_commits, stars, prs, issues):
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

def main():
    print("=" * 55)
    print(f"  Counting EVERY commit for @{USERNAME}")
    print("=" * 55)

    repos = all_repos()
    total_commits = 0
    stars = 0

    for i, repo in enumerate(repos):
        # Get actual owner of repo (might be org)
        owner = repo["owner"]["login"]
        name  = repo["name"]
        priv  = "private" if repo["private"] else "public"
        print(f"\n[{i+1}/{len(repos)}] {owner}/{name}  ({priv})")

        count = count_commits_in_repo(owner, name)
        print(f"  → {count:,} unique commits")
        total_commits += count
        stars += repo.get("stargazers_count", 0)

    print(f"\n{'='*55}")
    print(f"  TOTAL commits (ALL repos · ALL branches): {total_commits:,}")
    print(f"{'='*55}\n")

    prs    = search_count(f"type:pr author:{USERNAME}")
    issues = search_count(f"type:issue author:{USERNAME}")
    langs  = top_langs(repos)

    print(f"Stars={stars}  PRs={prs}  Issues={issues}")
    print(f"Top langs: {[l[0] for l in langs[:5]]}")

    block = build_stats_block(total_commits, stars, prs, issues)
    patch_readme(block)
    print(f"\n✅ Done! Total commits in README: {total_commits:,}")

if __name__ == "__main__":
    main()