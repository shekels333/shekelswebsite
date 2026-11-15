#!/usr/bin/env python3
"""Prove the redesign keeps every legacy outbound link and adds one.

Outbound means every absolute http(s) URL whose host is not shekels.me.
The redesign may add exactly https://www.4nbt.xyz/ (Luna). It must not
drop any legacy URL, and /legacy/ itself stays the archived page.
Run from the repo root:

    python3 scripts/check-outbound-links.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "legacy" / "index.html"
REDESIGN = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
ALLOWED_NEW = {"https://www.4nbt.xyz/"}

URL_RE = re.compile(r"https?://[^\s\"'<>]+")
ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.I)


def clean(url):
    return url.rstrip(").,;")


def host_of(url):
    return re.sub(r"^https?://", "", url).split("/")[0].lower()


def outbound(text):
    found = set()
    for raw in URL_RE.findall(text):
        url = clean(raw)
        host = host_of(url)
        if host == "shekels.me" or host.endswith(".shekels.me"):
            continue
        found.add(url)
    return found


def external_anchors_missing_attrs(text):
    bad = []
    for tag in ANCHOR_RE.findall(text):
        match = re.search(r'href=["\'](https?://[^"\']+)["\']', tag, re.I)
        if not match:
            continue
        href = match.group(1)
        host = host_of(href)
        if host == "shekels.me" or host.endswith(".shekels.me"):
            continue
        if "fonts.googleapis.com" in host or "fonts.gstatic.com" in host:
            continue
        if 'target="_blank"' not in tag or 'rel="noopener noreferrer"' not in tag:
            bad.append(href)
    return bad


def local_assets(text):
    missing = []
    for src in re.findall(r'(?:src|href)="(/[^"]+)"', text):
        path = ROOT / src.lstrip("/")
        if not path.exists():
            missing.append(src)
    return missing


def main():
    legacy_html = LEGACY.read_text()
    redesign_html = REDESIGN.read_text()
    old = outbound(legacy_html)
    new = outbound(redesign_html)
    only_old = sorted(old - new)
    only_new = sorted(new - old)

    print(f"legacy outbound URLs:   {len(old)}")
    print(f"redesign outbound URLs: {len(new)}")
    print("\nShared set:")
    for url in sorted(old & new):
        print(f"  {url}")
    print("\nOnly in legacy:")
    for url in only_old:
        print(f"  {url}")
    print("\nOnly in redesign:")
    for url in only_new:
        print(f"  {url}")

    problems = []
    if only_old:
        problems.append("redesign dropped legacy outbound links")
    if set(only_new) != ALLOWED_NEW:
        problems.append("redesign must add exactly https://www.4nbt.xyz/")
    if "https://www.4nbt.xyz/" in legacy_html:
        problems.append("legacy copy must stay unchanged and must not link Luna")
    if "Archived" not in legacy_html or "link-row archived" not in legacy_html:
        problems.append("legacy Luna row is no longer archived")

    bad_attrs = external_anchors_missing_attrs(redesign_html)
    if bad_attrs:
        problems.append("external anchors missing target=_blank rel=noopener noreferrer")
        for href in bad_attrs:
            print("BAD ANCHOR", href)

    head = legacy_html.split("</head>", 1)[0]
    if 'name="robots" content="noindex"' not in head:
        problems.append("legacy page is missing noindex")
    if "index, follow" in head:
        problems.append("legacy page still allows indexing")
    if 'rel="canonical" href="https://shekels.me/"' not in head:
        problems.append("legacy canonical is not https://shekels.me/")

    sitemap = SITEMAP.read_text()
    if "/legacy" in sitemap:
        problems.append("sitemap lists /legacy/")

    missing = local_assets(redesign_html)
    if missing:
        problems.append("redesign references missing local files")
        for src in missing:
            print("MISSING", src)

    if problems:
        print("\nFAIL:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nPASS: every legacy outbound link is kept, plus exactly https://www.4nbt.xyz/.")
    print("PASS: external anchors use target=_blank rel=noopener noreferrer.")
    print("PASS: /legacy/ is noindex, canonical https://shekels.me/, and absent from the sitemap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
