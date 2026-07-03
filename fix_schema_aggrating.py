#!/usr/bin/env python3
"""
fix_schema_aggrating.py
=======================
Perbaiki masalah GSC: "Jenis objek untuk kolom <parent_node> tidak valid"

Root cause:
  AggregateRating berdiri sendiri sebagai node di @graph.
  Google mensyaratkan AggregateRating harus di-nest sebagai
  PROPERTY di dalam entity induknya (LocalBusiness/Organization).

Fix yang dilakukan per file:
  1. Ambil data AggregateRating dari node terpisah
  2. Pindahkan sebagai property "aggregateRating" di dalam LocalBusiness
  3. Hapus node AggregateRating yang berdiri sendiri dari @graph
  4. Tulis ulang JSON-LD ke file HTML

Cara pakai:
  python3 fix_schema_aggrating.py           # dry-run
  python3 fix_schema_aggrating.py --write   # eksekusi
"""
import argparse, json, os, re
from pathlib import Path

HTML_DIRS = [
    ".",

]

JSONLD_RE = re.compile(
    r'(<script[^>]+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.DOTALL | re.IGNORECASE
)


def fix_schema(json_str: str) -> tuple[str, str]:
    """
    Perbaiki JSON-LD string.
    Return (fixed_json_str, status_message).
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return json_str, f"PARSE_ERROR: {e}"

    graph = data.get("@graph")
    if not graph:
        # Bukan format @graph — cek apakah punya aggregateRating langsung
        if "AggregateRating" in str(data.get("@type","")):
            return json_str, "SKIP: single AggregateRating node tanpa @graph"
        return json_str, "SKIP: tidak ada @graph"

    # Pisahkan node LocalBusiness dan AggregateRating
    lb_nodes  = [n for n in graph if any(
        t in str(n.get("@type",""))
        for t in ["LocalBusiness", "Organization"]
    )]
    agg_nodes = [n for n in graph if "AggregateRating" in str(n.get("@type",""))]
    other     = [n for n in graph if n not in lb_nodes and n not in agg_nodes]

    if not agg_nodes:
        return json_str, "SKIP: tidak ada AggregateRating"

    if not lb_nodes:
        return json_str, "SKIP: tidak ada LocalBusiness/Organization"

    agg = agg_nodes[0]

    # Sudah di-nest? Cek apakah LocalBusiness sudah punya aggregateRating property
    if "aggregateRating" in lb_nodes[0]:
        return json_str, "SKIP: aggregateRating sudah di-nest"

    # Buat aggregateRating property — tanpa @id dan itemReviewed (tidak diperlukan saat nested)
    agg_nested = {
        "@type":       "AggregateRating",
        "ratingValue": agg.get("ratingValue", "4.7"),
        "bestRating":  agg.get("bestRating",  "5"),
        "worstRating": agg.get("worstRating", "1"),
        "ratingCount": agg.get("ratingCount", "11"),
    }

    # Nest ke semua LocalBusiness node (biasanya cuma 1)
    for lb in lb_nodes:
        lb["aggregateRating"] = agg_nested
        # Hapus @id dari LB kalau sekarang jadi parent (opsional, tapi bersihkan)
        # Biarkan @id — masih berguna untuk BreadcrumbList reference

    # Rebuild @graph: LB (dengan rating nested) + node lain, tanpa AggregateRating standalone
    data["@graph"] = lb_nodes + other

    fixed = json.dumps(data, ensure_ascii=False, indent=None, separators=(',', ':'))
    return fixed, "FIXED"


def process_file(path: Path, write: bool) -> dict:
    content = path.read_text(encoding="utf-8")
    original = content

    matches = list(JSONLD_RE.finditer(content))
    if not matches:
        return {"file": path.name, "status": "NO_JSONLD"}

    status_all = []
    new_content = content

    for m in matches:
        open_tag  = m.group(1)
        json_str  = m.group(2).strip()
        close_tag = m.group(3)

        fixed_json, status = fix_schema(json_str)
        status_all.append(status)

        if status == "FIXED":
            new_script = f"{open_tag}{fixed_json}{close_tag}"
            new_content = new_content.replace(m.group(0), new_script, 1)

    changed = new_content != original
    final_status = "FIXED" if "FIXED" in status_all else status_all[0] if status_all else "NO_CHANGE"

    if write and changed:
        path.write_text(new_content, encoding="utf-8")

    return {"file": path.name, "status": final_status, "changed": changed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--dir",   action="append")
    args = parser.parse_args()

    dirs = HTML_DIRS + (args.dir or [])
    mode = "✏️  WRITE" if args.write else "👁️  DRY-RUN"

    print("=" * 60)
    print(f"fix_schema_aggrating.py — {mode}")
    print("=" * 60)

    all_files: list[Path] = []
    for d in dirs:
        p = Path(d)
        if not p.exists():
            print(f"  ⚠️  Folder tidak ditemukan: {d}")
            continue
        all_files.extend(sorted(p.glob("*.html")))

    print(f"File ditemukan: {len(all_files)}\n")

    results = []
    for fp in all_files:
        r = process_file(fp, write=args.write)
        results.append(r)
        icon = {"FIXED":"✅","SKIP":"➖","NO_JSONLD":"⚠️","NO_CHANGE":"➖"}.get(r["status"],"?")
        print(f"  {icon} [{r['status']:12}] {r['file']}")

    fixed   = sum(1 for r in results if r["status"] == "FIXED")
    skipped = sum(1 for r in results if r["status"].startswith("SKIP"))

    print(f"\n{'='*60}")
    print(f"  ✅ Fixed   : {fixed}")
    print(f"  ➖ Skipped : {skipped}")
    print(f"  Total      : {len(results)}")
    if not args.write:
        print(f"\n💡 DRY-RUN — jalankan ulang dengan --write untuk eksekusi")
    else:
        print(f"\n✅ Selesai! {fixed} file diperbaiki.")
    print("=" * 60)


if __name__ == "__main__":
    main()
