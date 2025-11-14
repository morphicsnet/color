#!/usr/bin/env python3
"""
check_docs_links.py

Validate intra-repo links and image paths in Markdown files under docs/.
- Checks [text](path) links and ![alt](path) images.
- Resolves relative paths from the file's directory.
- Ignores external (http/https), mailto, and anchor-only (#...) links.
- Percent-decodes paths (e.g., spaces encoded as %20) before checking.
- Exits with code 1 if any broken links or images are found.
Fuck you yeah who no wow fucking fuck shit oh shit heat
Usage:
  python tools/docs_lint/check_docs_links.py
  python tools/docs_lint/check_docs_links.py --root docs --verbose

This script uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import sys
import re
import os
from pathlib import Path
from urllib.parse import unquote

MD_LINK_RE = re.compile(r'(?P<img>!\[.*?\]|\[.*?\])\((?P<url>[^)\s]+)(?:\s+"[^"]*")?\)')
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:")
ANCHOR_PREFIX = "#"


def log(msg: str, verbose: bool):
    if verbose:
        print(msg)


def is_external(url: str) -> bool:
    u = url.strip()
    if not u:
        return True
    if u.startswith(SKIP_SCHEMES):
        return True
    if u.startswith(ANCHOR_PREFIX):  # anchor-only links
        return True
    return False


def normalize_and_check(md_file: Path, url: str, repo_root: Path) -> tuple[bool, Path | None, str]:
    """
    Resolve a relative URL from md_file directory and check file existence in repo.
    Returns: (exists, resolved_path_or_None, reason_if_missing)
    """
    # Handle percent-encoding (e.g., spaces as %20)
    decoded = unquote(url)

    # Some docs links intentionally start with "./" or "../"
    # Absolute repo paths are sometimes written without leading slash (e.g., docs/..., pdf/...)
    # Treat them as relative to the repository root when path starts with a known top-level prefix.
    top_level_prefixes = ("docs/", "pdf/", "coq/", "webapp/", "tools/", "build/", "examples/", "tests/", "dune-project", "Makefile")
    candidate: Path
    if any(decoded.startswith(p) for p in top_level_prefixes):
        candidate = (repo_root / decoded).resolve()
    else:
        # Resolve relative to the markdown file directory
        candidate = (md_file.parent / decoded).resolve()

    # Normalize by removing any URL fragments (e.g., file.md#section)
    candidate_str = str(candidate)
    if "#" in candidate_str:
        candidate = Path(candidate_str.split("#", 1)[0])

    # If it has a query (rare in repo links), strip it
    if "?" in candidate.name:
        candidate = candidate.with_name(candidate.name.split("?", 1)[0])

    # Check existence
    if candidate.exists():
        return True, candidate, ""
    else:
        return False, candidate, "Path does not exist"


def scan_markdown(md_file: Path, repo_root: Path, verbose: bool) -> list[dict]:
    """Return a list of broken link dicts for a single markdown file."""
    broken: list[dict] = []
    try:
        text = md_file.read_text(encoding="utf-8")
    except Exception as e:
        broken.append({
            "file": md_file,
            "url": None,
            "kind": "file-read-error",
            "reason": f"Failed to read: {e}"
        })
        return broken

    for m in MD_LINK_RE.finditer(text):
        raw = m.group(0)
        url = (m.group("url") or "").strip()
        is_img = raw.startswith("!")
        kind = "image" if is_img else "link"

        if not url or is_external(url):
            log(f"skip external/anchor in {md_file}: {url}", verbose)
            continue

        exists, resolved, reason = normalize_and_check(md_file, url, repo_root)
        if not exists:
            broken.append({
                "file": md_file,
                "url": url,
                "resolved": resolved,
                "kind": kind,
                "reason": reason
            })
        else:
            log(f"ok {kind} {url} -> {resolved}", verbose)
    return broken


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate Markdown links and images under docs/")
    ap.add_argument("--root", default="docs", help="Root directory to scan (default: docs)")
    ap.add_argument("--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args()

    repo_root = Path(os.getcwd()).resolve()
    scan_root = (repo_root / args.root).resolve()

    if not scan_root.exists():
        print(f"[error] scan root not found: {scan_root}", file=sys.stderr)
        return 2

    md_files = sorted(p for p in scan_root.rglob("*.md") if p.is_file())
    if not md_files:
        print(f"[warn] no markdown files found under {scan_root}", file=sys.stderr)
        return 0

    all_broken: list[dict] = []
    for md in md_files:
        broken = scan_markdown(md, repo_root, args.verbose)
        all_broken.extend(broken)

    if not all_broken:
        print(f"[ok] All links and images valid under {scan_root}")
        return 0

    # Report
    print(f"[fail] Found {len(all_broken)} broken link(s)/image(s):")
    for i, b in enumerate(all_broken, 1):
        file_rel = b["file"].relative_to(repo_root)
        url = b.get("url")
        resolved = b.get("resolved")
        kind = b.get("kind")
        reason = b.get("reason")
        print(f"  {i:03d}) {kind}: {url} in {file_rel}")
        if resolved:
            # Show resolved path relative to repo root for clarity
            try:
                resolved_rel = Path(resolved).relative_to(repo_root)
            except Exception:
                resolved_rel = resolved
            print(f"       -> resolved: {resolved_rel}")
        if reason:
            print(f"       reason: {reason}")

    return 1


if __name__ == "__main__":
    sys.exit(main())