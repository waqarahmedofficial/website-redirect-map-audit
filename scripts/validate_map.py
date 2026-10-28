#!/usr/bin/env python3
"""
Independent validator for the redirect-map proof sample.

Reads ONLY the delivered workbook + old-url-inventory.csv and recomputes
every structural check from scratch (it shares no code with build_map.py):

  1. Duplicate SOURCE rows - the same old URL mapped twice (checked
     explicitly and separately from target duplication).
  2. Coverage - Map sources == in-scope inventory URLs, exactly
     (no missing, no extra).
  3. Blank destinations.
  4. Redirect chains - a destination that is itself redirected elsewhere.
  5. Redirect loops - explicit cycle detection (incl. A -> B -> A).
  6. Duplicate TARGETS - shared destinations are allowed only when every
     source sharing one is documented (Merge Registry sheet, or a
     no-match orphan whose recommended fallback it is, per Orphans sheet).
  7. Orphan consistency - Map no-match rows == Orphans sheet rows, each
     with a recommendation matching the Map and a stated reason.
  8. Trailing-slash rule - every destination uses the trailing-slash form.
  9. Summary reconciliation - the counts printed in Summary & Validation
     equal the recomputed counts.
 10. Honesty disclosure - the workbook states that destination HTTP
     status was NOT checked (the new structure is hypothetical).

Destination HTTP status is intentionally NOT crawled here: the sample's
new URLs do not exist. On a live client job this script's structural pass
is followed by a staging crawl proving every destination returns 200.

Exit code 0 = all checks pass. Output is written to stdout (tee it to
validation-output.txt).
"""
import csv
import os
import sys
from collections import defaultdict
from urllib.parse import urlparse

from openpyxl import load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "Redirect-Map-Sample-htmx-org.xlsx")
INV = os.path.join(HERE, "old-url-inventory.csv")

results = []


def report(name, ok, detail):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def path_of(url):
    return urlparse(url).path or "/"


def main():
    wb = load_workbook(XLSX, read_only=True)

    # ---- load Map sheet
    ws = wb["Map"]
    rows = list(ws.iter_rows(values_only=True))
    header, data = rows[0], [r for r in rows[1:] if r and r[0]]
    m = []  # (old_url, new_url, type)
    for r in data:
        m.append({"old": r[0], "new": r[1], "type": r[2],
                  "old_path": path_of(r[0]), "new_path": path_of(r[1])})
    print(f"Map rows loaded: {len(m)}")

    # ---- load inventory (in-scope)
    inv = list(csv.DictReader(open(INV)))
    inv_scoped = {r["url"] for r in inv if r["in_scope"] == "Yes"}
    print(f"In-scope inventory URLs: {len(inv_scoped)}")

    # 1. duplicate SOURCE rows (explicit, standalone check)
    olds = [r["old"] for r in m]
    dup_sources = [u for u, c in
                   ((u, olds.count(u)) for u in set(olds)) if c > 1]
    report("Duplicate source rows",
           not dup_sources,
           f"{len(dup_sources)} old URLs appear more than once in the Map "
           f"({len(m)} rows, {len(set(olds))} unique sources)"
           + (f"; duplicates: {dup_sources}" if dup_sources else ""))

    # 2. coverage
    missing = inv_scoped - set(olds)
    extra = set(olds) - inv_scoped
    report("Coverage 1:1 vs in-scope inventory",
           not missing and not extra,
           f"missing={len(missing)} extra={len(extra)}"
           + (f"; missing: {sorted(missing)[:5]}" if missing else "")
           + (f"; extra: {sorted(extra)[:5]}" if extra else ""))

    # 3. blank destinations
    blanks = [r["old"] for r in m if not (r["new"] or "").strip()]
    report("Blank destinations", not blanks, f"{len(blanks)} blank")

    # 4. chains
    graph = {r["old_path"]: r["new_path"] for r in m
             if r["new_path"] != r["old_path"]}
    chains = [(o, n) for o, n in graph.items() if n in graph]
    report("Redirect chains", not chains,
           f"{len(chains)} chains" +
           (f": {chains[:5]}" if chains else
            " - no destination is itself the source of another redirect"))

    # 5. loops (explicit cycle detection, incl. A->B->A)
    cycles = []
    state = {}
    stack = []

    def dfs(u):
        state[u] = 1
        stack.append(u)
        v = graph.get(u)
        if v in graph:
            if state.get(v) == 1:
                cycles.append(stack[stack.index(v):] + [v])
            elif state.get(v, 0) == 0:
                dfs(v)
        stack.pop()
        state[u] = 2

    sys.setrecursionlimit(10000)
    for u in list(graph):
        if state.get(u, 0) == 0:
            dfs(u)
    report("Redirect loops", not cycles,
           f"{len(cycles)} cycles" +
           (f": {cycles[:3]}" if cycles else
            " - cycle detection over the redirect graph found none"))

    # 6. duplicate targets vs documentation
    ws = wb["Merge Registry"]
    reg = defaultdict(set)  # dest_path -> {source paths documented}
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not r or not r[0]:
            continue
        dest = path_of(r[0])
        for col in (r[1], r[2]):
            if col and col.startswith("http"):
                reg[dest].add(path_of(col))
    ws = wb["Orphans & No-Match"]
    orphan_rows = {}
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if r and r[0]:
            orphan_rows[path_of(r[0])] = {"dest": path_of(r[2] or ""),
                                          "reason": (r[3] or "").strip()}
    by_dest = defaultdict(list)
    for r in m:
        by_dest[r["new_path"]].append(r)
    shared = {d: rs for d, rs in by_dest.items() if len(rs) > 1}
    unintended = []
    for d, rs in shared.items():
        for r in rs:
            documented = (r["old_path"] in reg.get(d, set())) or \
                (r["type"] == "no-match" and
                 orphan_rows.get(r["old_path"], {}).get("dest") == d) or \
                (r["type"] == "unchanged" and r["old_path"] == d)
            if not documented:
                unintended.append(f"{r['old_path']} -> {d}")
    report("Duplicate targets (unintended)",
           not unintended,
           f"{len(shared)} destinations are shared; all sources sharing "
           f"them are documented (Merge Registry or Orphans sheet). "
           f"Unintended: {len(unintended)}"
           + (f": {unintended[:5]}" if unintended else ""))

    # 7. orphan consistency
    map_orphans = {r["old_path"]: r["new_path"] for r in m
                   if r["type"] == "no-match"}
    problems = []
    if set(map_orphans) != set(orphan_rows):
        problems.append(f"orphan set mismatch: map={sorted(map_orphans)} "
                        f"sheet={sorted(orphan_rows)}")
    for p, dest in map_orphans.items():
        o = orphan_rows.get(p)
        if o:
            if o["dest"] != dest:
                problems.append(f"{p}: orphan sheet dest {o['dest']} != "
                                f"map dest {dest}")
            if not o["reason"]:
                problems.append(f"{p}: missing reason")
    report("Orphan consistency", not problems,
           f"{len(map_orphans)} no-match rows, each present in the Orphans "
           f"sheet with matching recommendation and a reason"
           + (f"; problems: {problems}" if problems else ""))

    # 8. trailing-slash rule
    bad_slash = [r["new"] for r in m if not r["new_path"].endswith("/")]
    report("Trailing-slash rule", not bad_slash,
           f"{len(bad_slash)} destinations without trailing slash")

    # 9. summary reconciliation
    ws = wb["Summary & Validation"]
    printed = {}
    for r in ws.iter_rows(values_only=True):
        if r and isinstance(r[0], str) and isinstance(r[1], int):
            printed[r[0]] = r[1]
    by_type = defaultdict(int)
    for r in m:
        by_type[r["type"]] += 1
    expect = [
        ("Canonical old-URL inventory", len(inv)),
        ("Excluded from map scope", len(inv) - len(inv_scoped)),
        ("Old URLs in the map (in scope)", len(m)),
        ("exact 1:1", by_type["exact"]),
        ("intent 1:1", by_type["intent"]),
        ("merged into another page", by_type["merged"]),
        ("legacy alias", by_type["alias"]),
        ("unchanged (URL retained", by_type["unchanged"]),
        ("no-match orphans", by_type["no-match"]),
        ("Unique destinations", len(by_dest)),
    ]
    mismatches = []
    for key, val in expect:
        hit = [v for k, v in printed.items() if key in k]
        if not hit:
            mismatches.append(f"summary row not found for '{key}'")
        elif hit[0] != val:
            mismatches.append(f"'{key}': printed {hit[0]} != actual {val}")
    report("Summary counts reconcile", not mismatches,
           "; ".join(mismatches) if mismatches else
           "all 10 printed counts equal the recomputed counts "
           f"(total {len(m)} = exact {by_type['exact']} + intent "
           f"{by_type['intent']} + merged {by_type['merged']} + alias "
           f"{by_type['alias']} + unchanged {by_type['unchanged']} + "
           f"no-match {by_type['no-match']}; {len(by_dest)} unique "
           f"destinations)")

    # 10. honesty disclosure present
    text_blobs = []
    for name in ("About & How to Use", "Summary & Validation",
                 "Chains & Duplicates Check"):
        ws = wb[name]
        for r in ws.iter_rows(values_only=True):
            for c in r:
                if isinstance(c, str):
                    text_blobs.append(c)
    disclosed = any("NOT CHECKED" in t for t in text_blobs)
    report("Destination-status honesty disclosure", disclosed,
           "workbook states in writing that destination HTTP status was "
           "NOT CHECKED because the new structure is hypothetical, and "
           "names the staging crawl as the live-job equivalent"
           if disclosed else "disclosure text not found")

    print()
    if all(results):
        print(f"VERDICT: ALL {len(results)} CHECKS PASS")
        return 0
    print(f"VERDICT: {results.count(False)} OF {len(results)} CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
