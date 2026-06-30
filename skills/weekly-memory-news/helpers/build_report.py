#!/usr/bin/env python3
"""Deterministic report assembler for weekly-memory-news.

Reads:
  - <outputs_dir>/executive_summary.md
  - <outputs_dir>/companies/<slug>.md (one per company in --order)

Writes:
  - <outputs_dir>/report.md  ← single concatenated weekly report

Why a helper instead of an LLM concat: the model is allowed to write the
section files independently (so terminology stays consistent within each),
but the final stitching must be byte-deterministic so the auditor can
quote sections by line and so re-runs produce stable diffs.

Usage:
    python3 build_report.py \\
        --outputs-dir /abs/path/to/runs/<ts>/outputs \\
        --window-label "2026-06-23 ~ 2026-06-30" \\
        --order micron,sk-hynix,sandisk,kioxia
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _read_or_placeholder(path: Path, label: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8").rstrip() + "\n"
    return (
        f"## {label}\n\n"
        f"_({label} 섹션 누락 — 원본 파일 `{path.name}` 을 찾지 못했습니다.)_\n"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs-dir", type=Path, required=True)
    parser.add_argument("--window-label", type=str, required=True)
    parser.add_argument(
        "--order",
        type=str,
        required=True,
        help="Comma-separated company slugs in display order",
    )
    args = parser.parse_args(argv)

    outputs_dir: Path = args.outputs_dir
    if not outputs_dir.is_dir():
        print(f"not a directory: {outputs_dir}", file=sys.stderr)
        return 1

    slugs = [s.strip() for s in args.order.split(",") if s.strip()]
    if not slugs:
        print("--order produced no slugs", file=sys.stderr)
        return 2

    parts: list[str] = []
    parts.append(f"# 메모리 반도체 4사 주간 동향 — {args.window_label}\n")
    parts.append(
        "> 본 보고서는 공개된 웹 기사·보도자료를 기반으로 작성되었습니다. "
        "각 항목은 출처 URL 을 동반하며, 무출처 클레임은 포함하지 않습니다.\n"
    )

    exec_summary = outputs_dir / "executive_summary.md"
    parts.append("## 1. 임원용 핵심 요약 (1 페이지)\n")
    parts.append(_read_or_placeholder(exec_summary, "임원용 핵심 요약"))

    parts.append("## 2. 회사별 주요 발표\n")
    for slug in slugs:
        company_file = outputs_dir / "companies" / f"{slug}.md"
        parts.append(_read_or_placeholder(company_file, f"{slug} 섹션"))

    parts.append("---\n")
    parts.append(
        "_생성: `frame run weekly-memory-news` — 출처 검증은 `audit.md` 참고._\n"
    )

    target = outputs_dir / "report.md"
    target.write_text("\n".join(parts), encoding="utf-8")
    print(str(target))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
