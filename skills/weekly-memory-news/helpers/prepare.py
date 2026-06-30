#!/usr/bin/env python3
"""Deterministic run preparer for the weekly-memory-news skill.

Resolves two pieces of state the skill needs before issuing web searches:

1. The "last 7 days" window — start/end ISO dates plus a human-readable
   Korean label like `2026-06-23 ~ 2026-06-30`.
2. The watchlist — the set of memory companies to cover this run. Falls
   back to the canonical four (Micron, SK Hynix, SanDisk, Kioxia) when no
   override file is provided, otherwise reads one company per non-comment
   line from the override.

Output: JSON to stdout. Schema:

    {
      "window": {
        "end_iso":   "YYYY-MM-DD",
        "start_iso": "YYYY-MM-DD",
        "label_ko":  "YYYY-MM-DD ~ YYYY-MM-DD",
        "days":      7
      },
      "companies": [
        {"slug": "micron",  "name_en": "Micron",  "name_ko": "마이크론",
         "queries": ["Micron memory news", "마이크론 뉴스", ...]},
        ...
      ]
    }

Usage:
    python3 prepare.py                                  # defaults
    python3 prepare.py --watchlist path/to/watchlist.txt
    python3 prepare.py --now 2026-06-30                 # freeze "today" for tests
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DEFAULT_COMPANIES = [
    {
        "slug": "micron",
        "name_en": "Micron",
        "name_ko": "마이크론",
        "aliases": ["Micron Technology", "MU"],
    },
    {
        "slug": "sk-hynix",
        "name_en": "SK Hynix",
        "name_ko": "SK하이닉스",
        "aliases": ["SK Hynix", "Hynix", "하이닉스"],
    },
    {
        "slug": "sandisk",
        "name_en": "SanDisk",
        "name_ko": "샌디스크",
        "aliases": ["SanDisk Corporation", "WDC SanDisk"],
    },
    {
        "slug": "kioxia",
        "name_en": "Kioxia",
        "name_ko": "키오시아",
        "aliases": ["Kioxia Holdings", "KIOXIA"],
    },
]

SEARCH_TOPICS_EN = ["news", "announcement", "earnings", "HBM", "NAND", "DRAM"]
SEARCH_TOPICS_KO = ["뉴스", "발표", "실적"]


def _slugify(name: str) -> str:
    """ASCII-lowercase, non-alnum stripped, whitespace → hyphen."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9가-힣\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    return name or "company"


def _parse_watchlist(path: Path) -> list[dict]:
    """One company per non-comment, non-blank line.

    Recognises the canonical four by case-insensitive match; everything
    else becomes a custom entry whose Korean/English names are both the
    raw line (the skill can refine when emitting the report).
    """
    out: list[dict] = []
    known_by_alias = {}
    for c in DEFAULT_COMPANIES:
        for alias in [c["name_en"], c["name_ko"], *c["aliases"]]:
            known_by_alias[alias.lower()] = c

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = known_by_alias.get(line.lower())
        if match:
            if match not in out:
                out.append(match)
        else:
            out.append(
                {
                    "slug": _slugify(line),
                    "name_en": line,
                    "name_ko": line,
                    "aliases": [],
                }
            )
    return out or list(DEFAULT_COMPANIES)


def _build_queries(company: dict) -> list[str]:
    queries: list[str] = []
    en = company["name_en"]
    ko = company["name_ko"]
    for topic in SEARCH_TOPICS_EN:
        queries.append(f"{en} {topic}")
    for topic in SEARCH_TOPICS_KO:
        queries.append(f"{ko} {topic}")
    return queries


def _parse_now(value: str | None) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    # accept either YYYY-MM-DD or full ISO timestamps
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise SystemExit(f"invalid --now value: {value!r} ({exc})")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", type=Path, default=None)
    parser.add_argument("--now", type=str, default=None)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)

    if args.watchlist and args.watchlist.is_file():
        companies = _parse_watchlist(args.watchlist)
    else:
        companies = list(DEFAULT_COMPANIES)

    for c in companies:
        c["queries"] = _build_queries(c)

    end = _parse_now(args.now)
    start = end - timedelta(days=args.days)
    window = {
        "end_iso": end.isoformat(),
        "start_iso": start.isoformat(),
        "label_ko": f"{start.isoformat()} ~ {end.isoformat()}",
        "days": args.days,
    }

    print(
        json.dumps(
            {"window": window, "companies": companies},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
