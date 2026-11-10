#!/usr/bin/env python3
"""Render the profile README cards into cards/.

    python build_cards.py            # animated cards
    STATIC=1 python build_cards.py   # final frame only, for screenshots

Reads data/contributions.json ([{"date": "YYYY-MM-DD", "count": n}, ...]),
refreshed daily by .github/workflows/cards.yml. Drop a square portrait.jpg
(or .png) next to this file to show it in the hero.
"""
import base64, calendar, html, io, json, os, re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from fontTools import subset  # the library behind pyftsubset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).parent
STATIC = os.environ.get("STATIC") == "1"
W = 840
# realthejas.xyz palette: background, foreground, muted-foreground, border, bg-available
BG, FG, MUTED, LINE, BRAND = "#0a0a0a", "#fafafa", "#a1a1a1", "#ffffff1a", "#2ac45c"
LEVELS = (.06, .35, .55, .78, 1)  # graph cell opacity: empty, then brand quartiles
FONTS = {  # css class -> (family, file in fonts/)
    "serif": ("Instrument Serif", "InstrumentSerif-Regular.ttf"),
    "sans": ("Geist", "Geist-Regular.ttf"),
    "mono": ("Geist Mono", "GeistMono-Regular.ttf"),
}
TILES = [  # (file slug, label, value) - links live in README.md
    ("portfolio", "PORTFOLIO", "realthejas.xyz"),
    ("linkedin", "LINKEDIN", "in/thejasms"),
    ("email", "EMAIL", "Say hello"),
]
REPOS = [  # (repo, title, one-liner, stack, live host)
    ("moe-app", "MOE — Marketplace Aggregator",
     "Serverless marketplace aggregation on AWS, ~$1.50/month at 1k listings.",
     ["Next.js", "AWS CDK", "Lambda", "SQS", "DynamoDB", "Clerk"], "moe-app-web.vercel.app"),
    ("gitflow-ai", "Gitflow AI",
     "RAG knowledge engine that turns GitHub repos into searchable docs.",
     ["Next.js", "LangChain", "Gemini", "PostgreSQL", "pgvector"], "gitflow-ai.vercel.app"),
    ("DocSprint", "Doc Sprint",
     "Real-time collaborative editor with sub-100ms sync and live cursors.",
     ["Next.js", "Liveblocks", "TypeScript", "Tailwind"], "tms-doc-sprint.vercel.app"),
]

CSS = (f".serif{{font-family:'Instrument Serif',serif}}.sans{{font-family:Geist,sans-serif}}"
       f".mono{{font-family:'Geist Mono',monospace;letter-spacing:.06em}}"
       f".fg{{fill:{FG}}}.mu{{fill:{MUTED}}}.br{{fill:{BRAND}}}")
MOTION = (".in{animation:in .8s cubic-bezier(.2,.7,.2,1) both}"
          "@keyframes in{from{opacity:0;transform:translateY(10px)}}"
          ".grow{transform-box:fill-box;transform-origin:50% 100%;animation:grow .7s cubic-bezier(.2,.7,.2,1) both}"
          "@keyframes grow{from{transform:scaleY(0)}}"
          ".pop{transform-box:fill-box;transform-origin:center;animation:pop .35s ease-out both}"
          "@keyframes pop{from{opacity:0;transform:scale(.2)}}"
          # CSS can't pause SMIL, so SMIL-driven elements are hidden instead.
          "@media (prefers-reduced-motion:reduce){*{animation:none!important}.smil{display:none}}")


def at(t):
    return "" if STATIC else f' style="animation-delay:{t:.2f}s"'


def txt(x, y, s, cls, size, t, anchor="start"):
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" text-anchor="{anchor}" '
            f'class="{cls} in"{at(t)}>{html.escape(s)}</text>')


def arrow(x, y, t):  # ↗ as a path, so it never depends on glyph coverage
    return (f'<path d="M{x} {y + 12}L{x + 12} {y}M{x + 3} {y}H{x + 12}V{y + 9}" fill="none" '
            f'stroke="{MUTED}" stroke-width="1.5" class="in"{at(t)}/>')


def face(key, chars):
    family, file = FONTS[key]
    font = TTFont(ROOT / "fonts" / file)
    opts = subset.Options()
    opts.flavor, opts.hinting = "woff", False
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(chars))
    sub.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff;base64,{data}) format('woff')}}"


def card(name, h, title, body, w=W):
    chars = set(html.unescape(re.sub(r"<[^>]+>", "", body)))
    faces = "".join(face(k, chars) for k in FONTS if re.search(rf'class="[^"]*\b{k}\b', body))
    t = html.escape(title)
    (ROOT / "cards" / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{t}"><title>{t}</title><style>{faces}{CSS}{"" if STATIC else MOTION}</style>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}" stroke="{LINE}"/>'
        f"{body}</svg>")


def streaks(counts):
    cur = best = run = 0
    for c in counts:
        run = run + 1 if c else 0
        best = max(best, run)
    tail = counts[:-1] if counts and not counts[-1] else counts  # today may still be in progress
    for c in reversed(tail):
        if not c:
            break
        cur += 1
    return cur, best


def hero():
    b = [txt(40, 58, "PORTFOLIO / 2026", "mono mu", 12, 0),
         txt(40, 122, "Thejas Mandya Shashidhara", "serif fg", 54, .1),
         txt(40, 160, "Software engineer who ships. Full stack, AI/ML and distributed systems.", "sans mu", 16, .25),
         f'<circle cx="45" cy="191" r="4" class="br in"{at(.4)}/>',
         txt(58, 195, "AVAILABLE FOR WORK · NEW YORK CITY", "mono mu", 11, .4)]
    if not STATIC:
        pulse = 'dur="2s" begin="1s" repeatCount="indefinite"'
        b.append(f'<circle cx="45" cy="191" r="4" fill="none" stroke="{BRAND}" opacity="0" class="smil">'
                 f'<animate attributeName="r" values="4;12" {pulse}/>'
                 f'<animate attributeName="opacity" values=".8;0" {pulse}/></circle>')
    portrait = next((p for p in (ROOT / "portrait.jpg", ROOT / "portrait.png") if p.exists()), None)
    if portrait:
        mime = "jpeg" if portrait.suffix == ".jpg" else "png"
        img = base64.b64encode(portrait.read_bytes()).decode()
        b.append(f'<g class="in"{at(.2)}><clipPath id="p"><circle cx="740" cy="115" r="64"/></clipPath>'
                 f'<image href="data:image/{mime};base64,{img}" x="676" y="51" width="128" height="128" '
                 f'preserveAspectRatio="xMidYMid slice" clip-path="url(#p)"/>'
                 f'<circle cx="740" cy="115" r="64" fill="none" stroke="{LINE}"/></g>')
    card("hero", 230, "Thejas Mandya Shashidhara, software engineer", "".join(b))


def tiles():
    for i, (slug, label, value) in enumerate(TILES):
        t = .5 + i * .12
        card(f"tile-{slug}", 120, f"{label.title()}: {value}",
             txt(24, 40, label, "mono mu", 11, t) + arrow(234, 28, t) + txt(24, 92, value, "serif fg", 32, t + .1),
             w=270)


def activity(days):
    months = Counter()
    for d in days:
        months[d["date"][:7]] += d["count"]
    keys = sorted(months)[-12:]
    top = max(months[k] for k in keys) or 1
    counts = [d["count"] for d in days]
    cur, best = streaks(counts)
    busy = max(days, key=lambda d: d["count"])
    bd = date.fromisoformat(busy["date"])
    t0 = 1.0
    b = [txt(40, 44, "CONTRIBUTIONS / LAST 12 MONTHS", "mono mu", 11, t0),
         txt(40, 86, f"{sum(counts):,} contributions", "serif fg", 34, t0 + .05),
         f'<path d="M40 250.5H556M580.5 30V270" stroke="{LINE}"/>']
    slot = 516 / len(keys)
    for i, k in enumerate(keys):
        v, cx, t = months[k], 40 + slot * (i + .5), t0 + .2 + i * .05
        if v:
            h = max(2, 130 * v / top)
            b.append(f'<rect x="{cx - 13:g}" y="{250 - h:g}" width="26" height="{h:g}" rx="3" class="br grow"{at(t)}/>')
            b.append(txt(cx, 242 - h, str(v), "mono mu", 10, t + .3, "middle"))
        b.append(txt(cx, 272, calendar.month_abbr[int(k[5:])].upper(), "mono mu", 10, t, "middle"))
    stats = [(f"CURRENT STREAK · BEST {best}", f"{cur} day{'s' * (cur != 1)}"),
             ("ACTIVE DAYS", f"{sum(c > 0 for c in counts)} / {len(counts)}"),
             ("BUSIEST DAY", f"{calendar.month_abbr[bd.month]} {bd.day} · {busy['count']}")]
    for i, (label, value) in enumerate(stats):
        t, y = t0 + .3 + i * .15, 70 + i * 72
        b += [txt(610, y, label, "mono mu", 10, t), txt(610, y + 34, value, "serif fg", 32, t + .05)]
    card("activity", 300, f"{sum(counts)} contributions in the last year", "".join(b))


def repo_cards():
    for i, (repo, title, blurb, stack, host) in enumerate(REPOS):
        t = 1.8 + i * .25
        card(f"repo-{repo}", 170, f"{title}: {blurb}", "".join([
            f'<rect x="40" y="35" width="8" height="8" rx="2" class="br in"{at(t)}/>',
            txt(58, 44, f"REPO / {i + 1:02} · realthejas/{repo}", "mono mu", 11, t),
            txt(774, 44, host, "mono mu", 11, t, "end"), arrow(788, 32, t),
            txt(40, 94, title, "serif fg", 38, t + .08),
            txt(40, 124, blurb, "sans mu", 15, t + .16),
            txt(40, 150, "  ·  ".join(stack).upper(), "mono mu", 10, t + .24)]))


def graph(days):
    first = date.fromisoformat(days[0]["date"])
    start = first - timedelta((first.weekday() + 1) % 7)  # Sunday-first columns, like GitHub
    top = max(d["count"] for d in days) or 1
    ncols = (date.fromisoformat(days[-1]["date"]) - start).days // 7 + 1
    x0, t0 = (W - 14 * ncols + 3) / 2, 2.6
    b = [txt(x0, 30, "CONTRIBUTION GRAPH", "mono mu", 11, t0)]
    for d in days:
        dt = date.fromisoformat(d["date"])
        col, row, c = (dt - start).days // 7, (dt.weekday() + 1) % 7, d["count"]
        x, t = x0 + 14 * col, t0 + .1 + col * .012
        if dt.day == 1:
            b.append(txt(x, 50, calendar.month_abbr[dt.month].upper(), "mono mu", 10, t))
        lvl = -(-4 * c // top)  # 0..4, quartiles of the busiest day
        b.append(f'<rect x="{x:g}" y="{60 + 14 * row}" width="11" height="11" rx="2" fill="{BRAND if lvl else FG}" '
                 f'fill-opacity="{LEVELS[lvl]}" class="pop"{at(t)}/>')
    xr, t = W - x0 - 40, t0 + .1 + ncols * .012  # legend ends flush with the grid
    b.append(txt(xr - 5 * 14 - 8, 177, "LESS", "mono mu", 10, t, "end"))
    for i, op in enumerate(LEVELS):
        b.append(f'<rect x="{xr - (5 - i) * 14 + 3:g}" y="168" width="11" height="11" rx="2" '
                 f'fill="{BRAND if i else FG}" fill-opacity="{op}" class="in"{at(t)}/>')
    b.append(txt(xr + 8, 177, "MORE", "mono mu", 10, t))
    card("graph", 200, "Contribution graph for the last year", "".join(b))


if __name__ == "__main__":
    assert streaks([1, 0, 2, 3, 0]) == (2, 2)  # trailing zero = today, not a break
    assert streaks([1, 1, 0, 1]) == (1, 2)
    assert streaks([0, 0]) == (0, 0)
    days = json.loads((ROOT / "data" / "contributions.json").read_text())
    (ROOT / "cards").mkdir(exist_ok=True)
    hero(), tiles(), activity(days), repo_cards(), graph(days)
    print(f"wrote {len(list((ROOT / 'cards').glob('*.svg')))} cards{' (static)' if STATIC else ''}")
