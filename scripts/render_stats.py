#!/usr/bin/env python3
"""Render Irfan's GitHub stat cards as self-hosted SVGs.

Why this exists: github-readme-activity-graph and github-profile-trophy both
return 402 DEPLOYMENT_DISABLED, so the profile was showing two broken images.
These cards are generated from the GitHub GraphQL API in the repo's own CI and
committed to assets/, so nothing on the profile depends on a third-party host
staying alive.

Writes: assets/activity.svg, assets/rank.svg
Run:    GITHUB_TOKEN=<token> python3 scripts/render_stats.py
"""
import datetime as dt
import json
import os
import sys
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "irfan420x")
OUT = os.environ.get("OUT_DIR", "assets")

# palette (matches assets/hero.svg)
BG, PANEL = "#0b0918", "#07070d"
VIOLET, CYAN, GREEN, ROSE = "#a855f7", "#22d3ee", "#4ade80", "#f43f5e"
TXT, MUTED, FAINT = "#e6e6f0", "#8b93a7", "#5c6378"
LEVELS = ["#161022", "#241a3d", "#4c1d95", "#a855f7", "#22d3ee"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, first: 100) {
      totalCount
      nodes { stargazerCount forkCount }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def gql(token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "irfan420x-profile-stats"})
    with urllib.request.urlopen(req, timeout=45) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def level(count):
    if count == 0:
        return 0
    if count < 4:
        return 1
    if count < 9:
        return 2
    if count < 16:
        return 3
    return 4


def render_activity(cal, total):
    weeks = cal["weeks"]
    cell, gap = 13, 3
    left, top = 68, 74
    width = left + len(weeks) * (cell + gap) + 34
    height = top + 7 * (cell + gap) + 62

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"'
         f' viewBox="0 0 {width} {height}" fill="none">',
         '<style>@keyframes rise{0%,100%{opacity:.85}50%{opacity:.35}}.p{animation:rise 3.6s ease-in-out infinite}</style>',
         f'<rect width="{width}" height="{height}" rx="16" fill="{BG}"/>',
         f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" rx="16" fill="none" stroke="{VIOLET}" stroke-opacity="0.28" stroke-width="1.5"/>',
         f'<text x="24" y="40" font-family="ui-monospace,Menlo,monospace" font-size="15" font-weight="600" letter-spacing="2.4" fill="{VIOLET}">CONTRIBUTION HEATMAP</text>',
         f'<text x="{width - 24}" y="40" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="12" fill="{MUTED}">{total:,} in the last year</text>',
         f'<line x1="24" y1="54" x2="{width - 24}" y2="54" stroke="{VIOLET}" stroke-opacity="0.25"/>']

    # month labels
    seen = set()
    for wi, w in enumerate(weeks):
        days = w["contributionDays"]
        if not days:
            continue
        d = dt.date.fromisoformat(days[0]["date"])
        if d.month not in seen:
            seen.add(d.month)
            p.append(f'<text x="{left + wi * (cell + gap)}" y="{top - 8}" font-family="ui-monospace,Menlo,monospace" '
                     f'font-size="10.5" fill="{FAINT}">{d.strftime("%b")}</text>')

    for wi, w in enumerate(weeks):
        for day in w["contributionDays"]:
            x = left + wi * (cell + gap)
            y = top + day["weekday"] * (cell + gap)
            c = LEVELS[level(day["contributionCount"])]
            p.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>')

    ly = top + 7 * (cell + gap) + 24
    p.append(f'<text x="24" y="{ly + 10}" font-family="ui-monospace,Menlo,monospace" font-size="11" fill="{FAINT}">Less</text>')
    lx = 62
    for i, c in enumerate(LEVELS):
        p.append(f'<rect x="{lx + i * (cell + gap)}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>')
    p.append(f'<text x="{lx + 5 * (cell + gap) + 6}" y="{ly + 10}" font-family="ui-monospace,Menlo,monospace" font-size="11" fill="{FAINT}">More</text>')
    p.append(f'<circle class="p" cx="{width - 30}" cy="{ly + 6}" r="4" fill="{GREEN}"/>')
    p.append("</svg>")
    return "\n".join(p)


def render_rank(metrics):
    width, height = 900, 168
    n = len(metrics)
    slot = (width - 48) / n
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"'
         f' viewBox="0 0 {width} {height}" fill="none">',
         '<defs><linearGradient id="gl" x1="0" y1="0" x2="1" y2="0">'
         f'<stop offset="0%" stop-color="#ffffff"/><stop offset="45%" stop-color="{VIOLET}"/>'
         f'<stop offset="100%" stop-color="{CYAN}"/></linearGradient></defs>',
         f'<rect width="{width}" height="{height}" rx="16" fill="{BG}"/>',
         f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" rx="16" fill="none" stroke="{VIOLET}" stroke-opacity="0.28" stroke-width="1.5"/>',
         f'<text x="24" y="40" font-family="ui-monospace,Menlo,monospace" font-size="15" font-weight="600" letter-spacing="2.4" fill="{VIOLET}">ACTIVITY TELEMETRY</text>',
         f'<line x1="24" y1="54" x2="{width - 24}" y2="54" stroke="{VIOLET}" stroke-opacity="0.25"/>']

    for i, (label, value, colour) in enumerate(metrics):
        cx = 24 + slot * i + slot / 2
        p.append(f'<text x="{cx}" y="106" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" '
                 f'font-size="34" font-weight="700" fill="url(#gl)">{esc(value)}</text>')
        p.append(f'<text x="{cx}" y="132" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" '
                 f'font-size="10.5" letter-spacing="1.9" fill="{colour}">{esc(label)}</text>')
        if i:
            x = 24 + slot * i
            p.append(f'<line x1="{x}" y1="76" x2="{x}" y2="140" stroke="{VIOLET}" stroke-opacity="0.18"/>')

    p.append(f'<rect x="24" y="152" width="{width - 48}" height="2" rx="1" fill="url(#gl)" fill-opacity="0.55"/>')
    p.append("</svg>")
    return "\n".join(p)


def render_langs(langs):
    """Horizontal stacked bar + legend, built from the REST /languages endpoint."""
    total = sum(langs.values()) or 1
    width, height = 900, 176
    bar_x, bar_y, bar_w, bar_h = 24, 92, width - 48, 16
    colours = [VIOLET, CYAN, GREEN, ROSE, "#818cf8", "#facc15", "#2dd4bf", "#fb923c"]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"'
         f' viewBox="0 0 {width} {height}" fill="none">',
         f'<rect width="{width}" height="{height}" rx="16" fill="{BG}"/>',
         f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" rx="16" fill="none" stroke="{VIOLET}" stroke-opacity="0.28" stroke-width="1.5"/>',
         f'<text x="24" y="40" font-family="ui-monospace,Menlo,monospace" font-size="15" font-weight="600" letter-spacing="2.4" fill="{VIOLET}">LANGUAGE SPLIT</text>',
         f'<text x="{width - 24}" y="40" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="12" fill="{MUTED}">by bytes across public repos</text>',
         f'<line x1="24" y1="54" x2="{width - 24}" y2="54" stroke="{VIOLET}" stroke-opacity="0.25"/>',
         f'<clipPath id="barc"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="8"/></clipPath>',
         '<g clip-path="url(#barc)">', f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" fill="#161022"/>']

    items = list(langs.items()) if isinstance(langs, dict) else list(langs)
    x = bar_x
    for i, (name, n) in enumerate(items[:8]):
        w = bar_w * n / total
        p.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="{bar_h}" fill="{colours[i % len(colours)]}"/>')
        x += w
    p.append("</g>")

    for i, (name, n) in enumerate(items[:4]):
        cx = 24 + i * ((width - 48) / 4)
        pct = 100 * n / total
        p.append(f'<circle cx="{cx + 5}" cy="144" r="5" fill="{colours[i % len(colours)]}"/>')
        p.append(f'<text x="{cx + 18}" y="149" font-family="ui-monospace,Menlo,monospace" font-size="13" fill="{TXT}">{esc(name)}</text>')
        p.append(f'<text x="{cx + 18 + 9 * len(name)}" y="149" font-family="ui-monospace,Menlo,monospace" font-size="13" fill="{FAINT}"> {pct:.0f}%</text>')

    p.append("</svg>")
    return "\n".join(p)


def fetch_languages(token):
    """Sum language bytes over the account's public repos (REST, cheap)."""
    req = urllib.request.Request(
        f"https://api.github.com/users/{LOGIN}/repos?per_page=100&type=owner",
        headers={"Authorization": f"token {token}", "User-Agent": "irfan420x-profile-stats"})
    with urllib.request.urlopen(req, timeout=45) as r:
        repos = json.load(r)
    totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        rq = urllib.request.Request(
            repo["languages_url"],
            headers={"Authorization": f"token {token}", "User-Agent": "irfan420x-profile-stats"})
        try:
            with urllib.request.urlopen(rq, timeout=30) as r:
                for lang, n in json.load(r).items():
                    totals[lang] = totals.get(lang, 0) + n
        except Exception as e:                                   # noqa: BLE001
            print(f"  (skipped {repo['name']}: {e})", file=sys.stderr)
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]))


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not set")

    data = gql(token, QUERY, {"login": LOGIN})["user"]
    cal = data["contributionsCollection"]["contributionCalendar"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    forks = sum(r["forkCount"] for r in data["repositories"]["nodes"])
    cc = data["contributionsCollection"]

    os.makedirs(OUT, exist_ok=True)
    activity = render_activity(cal, cal["totalContributions"])
    rank = render_rank([
        ("CONTRIBUTIONS", f'{cal["totalContributions"]:,}', CYAN),
        ("COMMITS", f'{cc["totalCommitContributions"]:,}', VIOLET),
        ("PULL REQUESTS", f'{cc["totalPullRequestContributions"]:,}', GREEN),
        ("REPOSITORIES", f'{data["repositories"]["totalCount"]:,}', VIOLET),
        ("STARS EARNED", f"{stars:,}", CYAN),
    ])
    langs = fetch_languages(token)
    langs_svg = render_langs(langs)

    open(os.path.join(OUT, "activity.svg"), "w").write(activity)
    open(os.path.join(OUT, "rank.svg"), "w").write(rank)
    open(os.path.join(OUT, "langs.svg"), "w").write(langs_svg)
    print(f"wrote activity.svg ({len(activity)}b), rank.svg ({len(rank)}b), langs.svg ({len(langs_svg)}b)")
    print("top languages: " + ", ".join(f"{k} {v / max(sum(langs.values()), 1) * 100:.0f}%" for k, v in list(langs.items())[:6]))
    print(f"total={cal['totalContributions']} commits={cc['totalCommitContributions']} "
          f"prs={cc['totalPullRequestContributions']} issues={cc['totalIssueContributions']} "
          f"repos={data['repositories']['totalCount']} stars={stars} forks={forks} "
          f"followers={data['followers']['totalCount']}")


if __name__ == "__main__":
    main()
