#!/usr/bin/env python3
"""Generate the crawlable half of the site from the weekly backup.

index.html draws its gallery with JavaScript after fetching Supabase, so a
crawler's first look finds an empty <div> — no text, and crucially no images.
For a site that is entirely images, that leaves the most valuable thing it has
invisible to search.

So this emits a plain-HTML mirror: one page per film carrying its actual frames
as <img> tags with descriptive alt text, an index listing every film, and a
sitemap. Those pages are what search engines read and what Google Images can
pick up; the JavaScript gallery stays the way people actually browse.

Regenerated after each backup, so it tracks the collection as it grows.
"""

import html
import json
import os
import re
import unicodedata
import urllib.parse

SITE = "https://inomovyaxyo6-byte.github.io/gate-project/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STYLE = """
  :root{ color-scheme: dark; }
  body{
    margin:0; padding:48px 24px 72px;
    background:#0e0f10; color:#e8e6e3;
    font-family: ui-serif, Georgia, "Times New Roman", serif;
    line-height:1.5;
  }
  main{ max-width:960px; margin:0 auto; }
  h1{ font-size:28px; margin:0 0 6px; letter-spacing:0.02em; }
  .lede, .meta{
    color:#8d8a84; margin:0 0 32px; font-size:13px;
    font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  }
  a{ color:#e8c37a; text-decoration:none; }
  a:hover{ text-decoration:underline; }
  ul{ list-style:none; margin:0; padding:0; }
  li{ padding:14px 0; border-bottom:1px solid #22241f; }
  li a{ font-size:18px; }
  li .meta, li .count{
    display:block; margin:0; color:#8d8a84; font-size:13px;
    font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  }
  li .count{ color:#6f6d68; }
  figure{ margin:0 0 22px; }
  figure img{ width:100%; height:auto; display:block; border-radius:4px; background:#161718; }
  figcaption{
    color:#6f6d68; font-size:12px; margin-top:6px;
    font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  }
  .nav{ display:block; margin-top:40px; font-size:14px; }
"""


def load(name):
    with open(os.path.join(ROOT, "backup", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "film"


def collect(frames, covers):
    """Group frames by film the way the page does, by lowercased title."""
    cover_by_key = {c["movie_key"]: c["frame_id"] for c in covers}
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
            "actors": f.get("actors") or [],
            "frames": [],
            "added": "",
        })
        m["frames"].append(f)
        for g in f.get("genre") or []:
            if g and g not in m["genres"]:
                m["genres"].append(g)
        if (f.get("added_at") or "") > m["added"]:
            m["added"] = f.get("added_at") or ""

    used = set()
    for key, m in movies.items():
        base = slugify(m["title"])
        slug, n = base, 2
        # Titles are distinct today, but a collision must not silently
        # overwrite another film's page.
        while slug in used:
            slug = base + "-" + str(n)
            n += 1
        used.add(slug)
        m["slug"] = slug

        m["frames"].sort(key=lambda fr: fr.get("added_at") or "")
        cover_id = cover_by_key.get(key)
        cover = next((fr for fr in m["frames"] if fr.get("id") == cover_id), None)
        m["cover_url"] = (cover or m["frames"][0]).get("image_url") or ""

    return dict(sorted(movies.items(), key=lambda kv: kv[1]["title"].lower()))


def head(title, description, canonical, image=""):
    e = html.escape
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>" + e(title) + "</title>",
        '<meta name="description" content="' + e(description) + '">',
        '<link rel="canonical" href="' + e(canonical) + '">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Framelog">',
        '<meta property="og:title" content="' + e(title) + '">',
        '<meta property="og:description" content="' + e(description) + '">',
        '<meta property="og:url" content="' + e(canonical) + '">',
    ]
    if image:
        parts.append('<meta property="og:image" content="' + e(image) + '">')
    parts.append('<meta name="twitter:card" content="summary_large_image">')
    if image:
        parts.append('<meta name="twitter:image" content="' + e(image) + '">')
    parts += ["<style>" + STYLE + "</style>", "</head>", "<body>", "  <main>"]
    return "\n".join(parts)


def build_film_page(m):
    e = html.escape
    label = m["title"] + (" (" + m["year"] + ")" if m["year"] else "")
    meta = " · ".join(x for x in [m["year"], m["director"], ", ".join(m["genres"])] if x)
    description = str(len(m["frames"])) + " frames from " + label
    if m["director"]:
        description += ", directed by " + m["director"]
    description += "."

    # The alt text names the film because it is all Google Images has to go on.
    alt_base = "Still from " + label
    if m["director"]:
        alt_base += ", directed by " + m["director"]

    lines = [
        head(label + " — frames | Framelog", description,
             SITE + "films/" + m["slug"] + ".html", m["cover_url"]),
        "    <h1>" + e(label) + "</h1>",
        '    <p class="meta">' + e(meta) + " · " + str(len(m["frames"])) + " frames</p>",
    ]

    actors = ", ".join(m["actors"][:6])
    if actors:
        lines.append('    <p class="meta">Starring ' + e(actors) + "</p>")

    for i, fr in enumerate(m["frames"], 1):
        url = fr.get("image_url") or ""
        if not url:
            continue
        note = (fr.get("note") or "").strip()
        alt = alt_base + (" — " + note if note else " (frame " + str(i) + ")")
        lines.append("    <figure>")
        lines.append('      <img src="' + e(url) + '" alt="' + e(alt) + '" loading="lazy">')
        if note:
            lines.append("      <figcaption>" + e(note) + "</figcaption>")
        lines.append("    </figure>")

    deep_link = SITE + "?movie=" + urllib.parse.quote(m["title"].lower(), safe="")
    lines += [
        '    <a class="nav" href="' + e(deep_link) + '">Open in the gallery &rarr;</a>',
        '    <a class="nav" href="' + SITE + 'films.html">&larr; All films</a>',
        "  </main>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def build_index(movies, total_frames):
    e = html.escape
    description = ("Every film in the Framelog collection — " + str(len(movies))
                   + " films, " + str(total_frames) + " frames from their cinematography.")
    lines = [
        head("All films — Framelog", description, SITE + "films.html"),
        "    <h1>All films</h1>",
        '    <p class="lede">' + e(description) + "</p>",
        "    <ul>",
    ]
    for m in movies.values():
        meta = " · ".join(x for x in [m["year"], m["director"], ", ".join(m["genres"])] if x)
        n = len(m["frames"])
        lines += [
            "      <li>",
            '        <a href="' + SITE + "films/" + m["slug"] + '.html">' + e(m["title"]) + "</a>",
            '        <span class="meta">' + e(meta) + "</span>",
            '        <span class="count">' + str(n) + " frame" + ("" if n == 1 else "s") + "</span>",
            "      </li>",
        ]
    lines += [
        "    </ul>",
        '    <a class="nav" href="' + SITE + '">&larr; Open the gallery</a>',
        "  </main>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def build_sitemap(movies):
    # Only the static pages. Listing the ?movie= deep links as well would serve
    # the same content at two addresses, which reads as duplication.
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url><loc>" + SITE + "</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>",
        "  <url><loc>" + SITE + "films.html</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>",
    ]
    for m in movies.values():
        lastmod = (m["added"] or "")[:10]
        mod = "<lastmod>" + lastmod + "</lastmod>" if len(lastmod) == 10 else ""
        lines.append("  <url><loc>" + SITE + "films/" + m["slug"] + ".html</loc>"
                     + mod + "<priority>0.8</priority></url>")
    lines += ["</urlset>", ""]
    return "\n".join(lines)


def write(rel_path, text):
    full = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    frames = load("frames")
    movies = collect(frames, load("covers"))

    films_dir = os.path.join(ROOT, "films")
    os.makedirs(films_dir, exist_ok=True)
    keep = set(m["slug"] + ".html" for m in movies.values())
    # A renamed or deleted film shouldn't leave an orphan page behind.
    for stale in os.listdir(films_dir):
        if stale.endswith(".html") and stale not in keep:
            os.remove(os.path.join(films_dir, stale))

    for m in movies.values():
        write("films/" + m["slug"] + ".html", build_film_page(m))
    write("films.html", build_index(movies, len(frames)))
    write("sitemap.xml", build_sitemap(movies))

    images = sum(1 for f in frames if f.get("image_url"))
    print(str(len(movies)) + " film pages, " + str(images) + " images now in static HTML")


if __name__ == "__main__":
    main()
