#!/usr/bin/env python3
"""
Build the OLD-URL inventory for the redirect-map proof sample.

Site: https://htmx.org  (robots.txt explicitly allows all crawlers and
declares the sitemap; ~190 canonical URLs = small-to-medium site.)

Method:
  1. Fetch robots.txt + sitemap.xml (raw text, any content type).
  2. BFS-crawl internal links from the homepage (depth <= 4, HTML only,
     same host) to enrich the sitemap set: status, title, crawl depth,
     plus crawl-only discoveries.
  3. Fetch any sitemap URL the crawl never reached (status + title).
  4. CANONICALISATION PASS (deterministic, documented in METHOD doc):
     - Canonical form = https://htmx.org + path with trailing slash
       (the site's own server 301s non-slash forms to slash forms).
     - Slash variants and the bare domain fold into the canonical row;
       the fold is recorded in `notes`.
     - Query strings are NOT silently dropped: any query variant seen
       (e.g. /?suw=true) is recorded in `query_variants`. Canonical
       identity is path-based; the map governs paths.
     - A URL whose response redirects to a DIFFERENT canonical page is
       an alias (alias_target column), e.g. /attributes/kt-swap/ already
       301s to /attributes/hx-swap/ today.
     - Scope flags: test-harness area (/test...), off-site redirect
       endpoints (e.g. /discord -> discord.com) and URLs returning 404
       (broken link targets found by the crawl) are kept in the CSV as
       findings but marked in_scope = No with the reason in `notes`.

Polite crawl: single-threaded, 0.2s delay, honest UA, public pages only.
Idempotent: re-running rebuilds old-url-inventory.csv from scratch.
"""
import csv
import os
import time
import xml.etree.ElementTree as ET
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from lxml import html as lxml_html

BASE = "https://htmx.org"
HOST = "htmx.org"
UA = {"User-Agent": "RedirectMapSample/1.0 (portfolio research sample; light polite crawl)"}
DELAY = 0.2
MAX_DEPTH = 4
SKIP_EXT = (".xml", ".txt", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif",
            ".svg", ".ico", ".woff", ".woff2", ".zip", ".pdf", ".json")
HERE = os.path.dirname(os.path.abspath(__file__))

session = requests.Session()
session.headers.update(UA)


def get(url, need_html=True):
    """GET with polite delay -> (status, final_url, html_text_or_None, raw_text)."""
    time.sleep(DELAY)
    try:
        r = session.get(url, timeout=20, allow_redirects=True)
        raw = r.text
        ctype = r.headers.get("Content-Type", "")
        text = raw if (need_html and "text/html" in ctype) else None
        return r.status_code, r.url, text, raw
    except requests.RequestException as e:
        return f"ERR:{type(e).__name__}", url, None, ""


def parse_title(text):
    if not text:
        return ""
    try:
        doc = lxml_html.fromstring(text)
        t = doc.findtext(".//title")
        return " ".join(t.split()) if t else ""
    except Exception:
        return ""


def extract_links(text, base_url):
    if not text:
        return []
    try:
        doc = lxml_html.fromstring(text)
    except Exception:
        return []
    out = []
    for href in doc.xpath("//a/@href"):
        absu, _frag = urldefrag(urljoin(base_url, href))
        p = urlparse(absu)
        if p.netloc != HOST or p.scheme not in ("http", "https"):
            continue
        if p.path.lower().endswith(SKIP_EXT):
            continue
        out.append(absu)
    return out


def canon(url):
    """Canonical key: (path_with_trailing_slash). Query/fragment excluded
    from identity but recorded separately by the caller."""
    p = urlparse(url)
    path = p.path or "/"
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path


def main():
    # 1. robots + sitemap (raw text regardless of content type)
    status, _f, _h, robots = get(BASE + "/robots.txt", need_html=False)
    print(f"robots.txt status={status}; begins: {robots.strip()[:120]!r}")
    status, _f, _h, sm = get(BASE + "/sitemap.xml", need_html=False)
    root = ET.fromstring(sm.encode("utf-8"))
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = [e.text.strip() for e in root.findall(".//s:loc", ns)]
    sitemap_canon = {canon(u): u for u in sitemap_urls}
    print(f"sitemap URLs: {len(sitemap_urls)}")

    # 2. BFS crawl (raw URLs as linked, fragments stripped, queries kept)
    depth = {BASE + "/": 0}
    raw_seen = {}  # raw url -> dict(status, final_url, title)
    queue = deque([BASE + "/"])
    while queue:
        url = queue.popleft()
        d = depth[url]
        status, final_url, text, _raw = get(url)
        raw_seen[url] = {"status": status, "final_url": final_url,
                         "title": parse_title(text)}
        if text and d < MAX_DEPTH:
            for link in extract_links(text, url):
                if link not in depth:
                    depth[link] = d + 1
                    queue.append(link)
    print(f"crawl visited {len(raw_seen)} raw URLs")

    # 3. sitemap URLs never crawled -> fetch once
    crawled_canon = {canon(u) for u in raw_seen}
    for path, u in sitemap_canon.items():
        if path not in crawled_canon:
            status, final_url, text, _raw = get(u)
            raw_seen[u] = {"status": status, "final_url": final_url,
                           "title": parse_title(text)}
    print(f"raw URLs after sitemap fill-in: {len(raw_seen)}")

    # 4. canonicalisation pass
    groups = {}  # canon path -> list of (raw_url, info)
    for u, info in raw_seen.items():
        groups.setdefault(canon(u), []).append((u, info))

    rows = []
    for path in sorted(groups):
        members = groups[path]
        curl = BASE + path
        # status/title: prefer the member that IS the canonical URL,
        # else a member whose final_url canonicalises to this path.
        pick = None
        for u, info in members:
            if u == curl:
                pick = info
                break
        if pick is None:
            for u, info in members:
                if canon(info["final_url"]) == path and \
                        urlparse(info["final_url"]).netloc == HOST:
                    pick = info
                    break
        if pick is None:
            pick = members[0][1]
        status = pick["status"]
        title = pick["title"]

        # alias / offsite detection: canonical fetch redirected elsewhere
        alias_target = ""
        offsite = ""
        for u, info in members:
            fu = info["final_url"]
            if urlparse(fu).netloc not in (HOST, ""):
                offsite = fu
            elif canon(fu) != path and canon(fu) != canon(u):
                alias_target = BASE + canon(fu)
        # a member that was itself the canonical and redirected elsewhere
        for u, info in members:
            if u == curl and canon(info["final_url"]) != path and \
                    urlparse(info["final_url"]).netloc == HOST:
                alias_target = BASE + canon(info["final_url"])

        query_variants = sorted({urlparse(u).query for u, _i in members
                                 if urlparse(u).query})
        variants = sorted({u for u, _i in members if u != curl})
        dep = min([depth[u] for u, _i in members if u in depth], default="")
        src = []
        if path in sitemap_canon:
            src.append("sitemap")
        if any(u in depth for u, _i in members):
            src.append("crawl")

        notes = []
        in_scope = "Yes"
        if variants:
            notes.append("Also linked in non-canonical form(s): " +
                         ", ".join(variants[:3]))
        if query_variants:
            notes.append("Query variant(s) seen in crawl: " +
                         ", ".join("?" + q for q in query_variants) +
                         " (map governs the path; query handling per stated rule)")
        if alias_target:
            notes.append(f"Already redirects today to {alias_target} "
                         "(legacy alias - map follows its target page)")
        if offsite:
            in_scope = "No"
            notes.append(f"Off-site redirect endpoint (redirects to {offsite}); "
                         "not a content page - excluded from map scope")
        if path.startswith("/test"):
            in_scope = "No"
            notes.append("Test-harness area, not public content - excluded "
                         "from redesign scope (recommend noindex/removal)")
        if str(status) != "200":
            in_scope = "No"
            notes.append(f"Returns HTTP {status} today - broken link target "
                         "found by crawl; nothing live to preserve, fix the "
                         "linking page instead")

        section = path.strip("/").split("/")[0] if path.strip("/") else "(root)"
        rows.append({
            "url": curl, "path": path, "status_code": status,
            "page_title": title, "depth": dep, "source": "+".join(src),
            "section": section, "in_scope": in_scope,
            "alias_target": alias_target,
            "query_variants": ";".join(query_variants),
            "notes": " | ".join(notes),
        })

    out = os.path.join(HERE, "old-url-inventory.csv")
    fields = ["url", "path", "status_code", "page_title", "depth", "source",
              "section", "in_scope", "alias_target", "query_variants", "notes"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    in_rows = [r for r in rows if r["in_scope"] == "Yes"]
    out_rows = [r for r in rows if r["in_scope"] == "No"]
    print(f"\nCANONICAL INVENTORY: {len(rows)} URLs")
    print(f"  in scope for the map: {len(in_rows)}")
    print(f"  out of scope (documented findings): {len(out_rows)}")
    for r in out_rows:
        print(f"    - {r['url']} [{r['status_code']}] {r['notes'][:90]}")
    print(f"  raw crawl discoveries folded as variants: "
          f"{sum(1 for r in rows if 'non-canonical' in r['notes'])} pages")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
