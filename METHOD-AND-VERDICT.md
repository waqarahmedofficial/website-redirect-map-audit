# Redirect-Map Proof Sample — Method & Verdict

**Built:** 24 October 2026 · **Site mapped:** [htmx.org](https://htmx.org) · **Deliverable:** `Redirect-Map-Sample-htmx-org.xlsx`

> This is a **proof sample, not a client job**. The old structure is real (collected live from the site). The new structure is a **hypothetical redesign invented for this sample**. Nobody at htmx.org commissioned, reviewed, or has even seen it. Nothing here may be presented as client work.

---

## 1. Why this site

htmx.org was chosen because it is a real, public, small-to-medium website whose `robots.txt` explicitly allows all crawlers (`Disallow:` empty, `Allow: /`) and declares its own sitemap. Its sitemap lists 188 URLs across clear sections (documentation, attribute reference, essays, examples, extensions, release notes) — exactly the shape of a site an agency might redesign. Public pages only; no logins; nothing behind any barrier; single-threaded crawl with delays (polite rate).

## 2. How the old-URL inventory was built (`build_inventory.py`)

1. Fetched `robots.txt` and `sitemap.xml` (188 URLs).
2. Breadth-first crawl of internal links from the homepage (depth ≤ 4, HTML pages only, same host), recording live HTTP status, page title and crawl depth for every URL — 222 raw URL forms were fetched in total.
3. Fetched any sitemap URL the crawl never reached (5 pages, e.g. the section indexes `/attributes/`, `/headers/`, `/posts/` and the security advisory `/CVE-2026-3682-1/`).
4. **Canonicalisation pass** (deterministic, and the single most valuable step in the whole exercise):
   - The site's own server 301-redirects non-slash forms to trailing-slash forms, so the **canonical form is the trailing-slash URL**. Slash variants and the bare domain fold into the canonical row, and the fold is recorded in the inventory's notes. (The raw crawl found the same page linked both ways dozens of times — a naive inventory would have double-counted ~30 pages.)
   - **Query strings are preserved, not stripped**: variants seen are recorded in a `query_variants` column (one found: `/?suw=true` on the homepage). Canonical identity is path-based; the map governs paths, and the rule is stated in the workbook.
   - **Aliases are detected from live behaviour**: `/attributes/kt-swap/` already 301s to `/attributes/hx-swap/` today, so it is flagged `alias_target` and, in the map, follows its target page to the same destination.
   - A bonus real-world find of exactly the kind migrations exist to catch: the sitemap lists the advisory as `/CVE-2026-3682-1/` (upper case) while the server canonicalises it to lower case.

**Inventory result: 197 canonical URLs → 189 in scope for the map, 8 excluded with documented reasons:**

| Excluded | Reason |
|---|---|
| `/attributes/hx-sse/`, `/attributes/hx-ws/`, `/manual/`, `/extensions/idiomorph/@attributes/hx-swap/` (4) | Return **404 today** — broken link targets discovered by the crawl (one is a malformed relative link inside the idiomorph extension page). Nothing live to preserve; the fix is on the linking page. Reported as findings. |
| `/test/`, `/test/manual/`, `/test/scratch/scratch/` (3) | The project's public test-harness area — not content; excluded from redesign scope (recommend noindex/removal). |
| `/discord/` (1) | Off-site redirect shim, not a page (the discovery crawl verified it redirects to a discord.com invite; in the canonical run the off-site follow timed out, so its status cell honestly records that timeout — it is out of scope either way). |

Provenance per canonical URL: 183 found by both sitemap and crawl, 5 sitemap-only, 9 crawl-only (of which exactly **1 in-scope page — the kt-swap alias — came from the crawl alone**, a good sign the sitemap is near-complete for this site).

## 3. The hypothetical new structure (sample invention)

Same domain, trailing-slash URLs throughout. Design decisions a real redesign would plausibly make:

- `/docs/` → **`/guide/`** hub; the two current-version migration guides become Guide sub-pages.
- `/attributes/` and `/headers/` consolidate under **`/reference/`** (joining `/reference/` and `/api/`).
- `/extensions/` → **`/addons/`**; `/examples/` → **`/showcase/`**; `/essays/` → **`/writing/`**; `/posts/` → **`/releases/`** with cleaned slugs (date prefix and `-is-released` suffix removed, e.g. `/posts/2024-06-17-htmx-2-0-0-is-released/` → `/releases/htmx-2-0-0/`).
- **Merges (8 rows, all in the workbook's Merge Registry):** three framework-specific modal demos → one combined `/showcase/modals/` page; the file-upload input variant folds into the main file-upload example; the move-before details sub-page folds into its parent; `/essays/all/` folds into the Writing index; `/server-examples/` and `/quirks/` fold into the Guide hub.
- **Hard cases kept deliberately (5 no-match orphans):** the one-off security advisory, the webring page, the talk page, the events page, and the predecessor-library (Intercooler) migration guide have no equivalent in the new structure. Each sits in the Orphans & No-Match sheet with a recommended fallback destination and a written reason; in the Map its destination column carries that recommended fallback so the map stays implementable.

## 4. Exact results

| Count | Value |
|---|---|
| Canonical inventory | 197 |
| In scope / map rows | **189** |
| — exact 1:1 (slug preserved) | 128 |
| — intent 1:1 (closest equivalent) | 45 |
| — merged (registered) | 8 |
| — legacy alias following its target | 1 |
| — unchanged (URL retained) | 2 |
| — no-match orphans (fallback given) | 5 |
| Unique destinations | 176 |
| Shared destinations | 8 — **all documented** (Merge Registry groups + orphan fallbacks) |
| Coverage of in-scope inventory | 100%, every URL exactly once |

## 5. Validation (`validate_map.py`, output in `validation-output.txt`)

The validator is independent of the builder: it reads only the delivered workbook and the inventory CSV and recomputes everything. **All 10 checks PASS:**

1. Duplicate **source** rows: **0** (189 rows, 189 unique sources — checked explicitly and separately from target duplication, because a doubled source is the first thing buyers look for).
2. Coverage 1:1 vs in-scope inventory: no missing, no extra.
3. Blank destinations: 0.
4. Redirect **chains**: 0.
5. Redirect **loops**: 0 — explicit cycle detection (depth-first) over the redirect graph, not just chain-following.
6. Unintended duplicate **targets**: 0 — every shared destination is documented (merges/alias in the Merge Registry; orphan fallbacks in the Orphans sheet; a retained page owns its own URL).
7. Orphan consistency: the 5 Map no-match rows match the Orphans sheet exactly, each with recommendation + reason.
8. Trailing-slash rule: every destination in trailing-slash form.
9. Summary reconciliation: all 10 counts printed in the workbook equal the recomputed counts.
10. Honesty disclosure present (see §6).

One validator refinement worth noting: the first run flagged the two *unchanged* pages (`/` and `/reference/`) as "undocumented" sharers of their own URLs, because orphan fallbacks also point at them. That was a semantics bug in the check, not a map error — a retained page owns its URL — and both the builder and validator now encode that rule explicitly.

## 6. Honest limits — what this sample does NOT prove

- **Destination status was NOT checked, and cannot be in a sample.** The new URLs are hypothetical, so they return 404 today by definition. The workbook says this in writing in three places (About, Chains & Duplicates Check, Summary & Validation) rather than silently passing the check. On a live client job this becomes a real step: a staging crawl proving **every destination returns HTTP 200** before launch. Our validation script covers the structural half of that proof; the live half only exists when a staging site exists.
- **The new structure is invented.** A real job starts from the client's/agency's actual new sitemap; the mapping judgement (which page is the "closest equivalent") would be reviewed against real content and analytics, which a sample cannot access.
- **No traffic/backlink weighting.** Which orphans matter most commercially depends on the client's analytics and backlink data — the agency supplies that on a real job; the sample ranks nothing by traffic.
- **Crawl completeness boundary:** inventory = sitemap + internal links within depth 4. Pages in neither would be missed. On client jobs the standard extra source is the client's server-log / analytics URL export, which we'd request.
- **Pricing is not proven by this sample.** Map-only pricing remains an *inference* from the full-migration market documented in the niche research (UK website migrations £1,000–£5,000 including URL mapping; US redirect mapping at $150/hr; migration reviews $1,999–$12,500). A standalone map will price below those full-service numbers, in a four-figure slice at best. **No buyer has seen this sample; no price has been tested.**
- **Demand evidence is unchanged by this build.** The "low competition for map-only work" claim rests on the earlier research (search/directory scarcity of map-only sellers), not on anything this sample demonstrates.
- Statuses and titles are a snapshot of 24 October 2026; the live site changes (one URL's fetch even timed out between our two crawls).

## 7. PERFORMABILITY VERDICT — ✅ YES, proven end-to-end for the deliverable as scoped

Every production step of the sold deliverable was executed for real, at zero cost, with free tooling (Python + openpyxl), no client-system access, and no step requiring the seller to speak, appear, or attend anything:

`sitemap + polite crawl → canonicalisation (slash/query/alias handling) → mapping rules with documented exceptions → professionally formatted workbook (frozen headers, filters, six sheets) → independent machine validation, 10/10 checks pass.`

The pipeline is scripted and re-runnable (`build_inventory.py`, `build_map.py`, `validate_map.py`), so a real agency job is a re-run with the client's real new sitemap plus analyst judgement on intent matches — the judgement this sample exercised 45 times (intent), 8 times (merges) and 5 times (orphans).

**What remains unproven is commercial, not technical:** whether agencies will buy the map unbundled from migration delivery, and at what price. That is a pitch question, and it is exactly what this sample now exists to ask — with a verified workbook in hand instead of a claim.
