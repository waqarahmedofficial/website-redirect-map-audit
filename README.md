# Website Redirect Map Audit — Migration-Ready URL Mapping

**A complete, independently validated redirect map for your website migration — every old URL accounted for exactly once, with zero chains and zero loops.**

Built by **Waqar Ahmed**, spreadsheet & data specialist (7+ years: data cleaning, validation, reconciliation and reporting for businesses and agencies).

## Who this is for

Agencies and site owners planning a redesign, replatform or restructure who need the URL mapping done properly *before* launch — the step that protects SEO equity and stops "we lost traffic after the migration" from happening.

## What the proof in this repo shows

A full redirect map built for a real, public website (htmx.org — chosen because its sitemap + crawl shape matches a typical agency redesign). The old structure is real, collected live from the site; the new structure is a clearly-labelled hypothetical redesign created for this sample. Nobody commissioned this map — it is a proof of capability, and it says so inside the workbook itself.

| Measure | Result |
|---|---|
| Canonical old-URL inventory | **197 URLs** (sitemap + polite crawl, canonicalised: trailing-slash forms, query variants recorded, live aliases detected) |
| Map rows delivered | **189** (8 exclusions documented with reasons: 404s found, test area, off-site shim) |
| — Exact 1:1 matches | 128 |
| — Intent 1:1 matches (closest equivalent, judged) | 45 |
| — Merged pages (all registered) | 8 |
| — Legacy alias following its target | 1 |
| — Unchanged URLs | 2 |
| — No-match orphans (each with a recommended fallback + written reason) | 5 |
| Unique destinations | 176 |
| Independent validation | **10/10 checks PASS** (`validation-output.txt`) |

The validator is independent of the builder — it re-reads only the delivered workbook and the inventory and recomputes everything: duplicate sources (0), 1:1 coverage, blank destinations (0), **redirect chains (0)**, **redirect loops (0, by explicit cycle detection)**, undocumented shared targets (0), orphan consistency, and summary-count reconciliation.

Files: the deliverable workbook (`Redirect-Map-Sample-htmx-org.xlsx`), the canonical inventory (`old-url-inventory.csv`), the full method + honest limits (`METHOD-AND-VERDICT.md`), the validator output, and the re-runnable pipeline scripts (`scripts/`).

## What you receive on a real engagement

- A professionally formatted Excel workbook: the redirect map, the merge registry, the orphans & no-match sheet (each with a recommended fallback and reason), and a checks sheet
- A canonical inventory of your current URLs (sitemap + crawl + your analytics/log exports if you supply them)
- Independent machine validation of the finished map — coverage, chains, loops, duplicates — with the output included
- Findings the crawl surfaces along the way (existing 404s, alias quirks, non-canonical forms)

## How the work runs

1. **Inputs in writing** — your current site URL and the new sitemap/structure from your redesign (plus analytics or server-log URL exports if available).
2. **Inventory** — sitemap + polite crawl, then canonicalisation (slash/query/alias handling) so no page is double-counted or missed.
3. **Mapping** — documented rules first, analyst judgement where judgement is needed (intent matches, merges, orphans) — every judgement is written down, not hidden.
4. **Validation** — the independent checker runs over the finished map; anything unreconciled is reported, never buried.
5. **Delivery** — workbook + validation output, ready for your developer to implement.

Straight about one limit: destination URLs can only be proven live (HTTP 200) once your staging site exists — on a real engagement that staging crawl is part of the job. The structural half of the proof is what this sample demonstrates.

## Tools

Python · openpyxl · Excel / Google Sheets

## About this sample

Proof of capability, built from public website data only. Full method, judgement calls and honest limits are documented in `METHOD-AND-VERDICT.md` — including what a sample cannot prove.

## Work with me

I take on freelance projects through Contra: **https://contra.com/mr_world_z7lsrx86**

Communication is **written-only** (chat/email) — clear briefs, documented handovers, no calls needed. Payment via Payoneer or bank transfer.
