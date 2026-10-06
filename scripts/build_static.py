#!/usr/bin/env python3
"""Generate the crawlable parts of the site from the weekly backup.

The gallery itself is drawn by JavaScript after fetching Supabase, so a search
engine's first look at index.html finds an empty <div> and nothing to index.
These two files give it real text instead: a static list of every film, and a
sitemap pointing at each one.

Run after the backup step, so the output tracks the collection as it grows.
"""

import html
import json
import os
import urllib.parse

SITE = "https://inomovyaxyo6-byte.github.io/gate-project/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "backup", f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def collect_movies(frames):
    """Group frames the way the page does: by lowercased title."""
    movies = {}
    for f in frames:
        title = (f.get("movie_title") or "").strip()
        if not title:
            continue
        key = title.lower()
        m = movies.setdefault(key, {
            "title": title,
            "year": f.get("year") or "",
            "director": f.get("director") or "",
            "genres": [],
            "count": 0,
            "added": "",
        })
        m["count"] += 1
        for g in (f.get("genre") or []):
            if g and g not in m["genres"]:
                m["genres"].append(g)
        added = f.get("added_at") or ""
        if added > m["added"]:
            m["added"] = added
    return dict(sorted(movies.items(), key=lambda kv: kv[1]["title"].lower()))


def movie_url(key):
    return SITE + "?movie=" + urllib.parse.quote(key, safe="")


def build_films_page(movies, total_frames):
    e = html.escape
    rows = []
    for key, m in movies.items():
        meta = " · ".join(x for x in [m["year"], m["director"], ", ".join(m["genres"])] if x)
        rows.append(
            f'      <li>\n'
            f'        <a href="{e(movie_url(key))}">{e(m["title"])}</a>\n'
            f'        <span class="meta">{e(meta)}</span>\n'
            f'        <span class="count">{m["count"]} frame{"" if m["count"] == 1 else "s"}</span>\n'
            f'      </li>'
        )
    listing = "\n".join(rows)
    description = (
        f"Every film in the GATE collection — {len(movies)} films, "
        f"{total_frames} frames from their cinematography."
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>All films — GATE</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{SITE}films.html">
<style>
  :root{{ color-scheme: dark; }}
  body{{
    margin:0; padding:48px 24px 72px;
    background:#0e0f10; color:#e8e6e3;
    font-family: ui-serif, Georgia, "Times New Roman", serif;
    line-height:1.5;
  }}
  main{{ max-width:720px; margin:0 auto; }}
  h1{{ font-size:28px; margin:0 0 6px; letter-spacing:0.02em; }}
  .lede{{ color:#9a9690; margin:0 0 36px; font-size:15px; }}
  ul{{ list-style:none; margin:0; padding:0; }}
  li{{ padding:14px 0; border-bottom:1px solid #22241f; }}
  a{{ color:#e8c37a; text-decoration:none; font-size:18px; }}
  a:hover{{ text-decoration:underline; }}
  .meta, .count{{
    display:block; color:#8d8a84; font-size:13px;
    font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  }}
  .count{{ color:#6f6d68; }}
  .back{{ display:inline-block; margin-top:36px; font-size:14px; }}
</style>
</head>
<body>
  <main>
    <h1>All films</h1>
    <p class="lede">{html.escape(description)}</p>
    <ul>
{listing}
    </ul>
    <a class="back" href="{SITE}">&larr; Open the gallery</a>
  </main>
</body>
</html>
"""


def build_sitemap(movies):
    e = html.escape
    urls = [f"  <url><loc>{SITE}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>",
            f"  <url><loc>{SITE}films.html</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"]
    for key, m in movies.items():
        lastmod = (m["added"] or "")[:10]
        mod = f"<lastmod>{lastmod}</lastmod>" if len(lastmod) == 10 else ""
        urls.append(f"  <url><loc>{e(movie_url(key))}</loc>{mod}<priority>0.6</priority></url>")
    body = "\n".join(urls)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""


def main():
    frames = load("frames")
    movies = collect_movies(frames)

    with open(os.path.join(ROOT, "films.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(build_films_page(movies, len(frames)))
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(build_sitemap(movies))

    print(f"films.html + sitemap.xml: {len(movies)} films, {len(frames)} frames")


if __name__ == "__main__":
    main()
