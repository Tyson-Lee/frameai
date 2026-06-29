#!/usr/bin/env python3
"""Deterministic transcript preprocessor for the meeting-summarizer skill.

Reads one transcript file (.vtt, .txt, .md), normalizes it to a single
cleaned text blob, and detects whether the language is Korean or English.

Output: JSON to stdout — keys `lang`, `text`, `speakers`, `lines`.

Usage:
    python3 preprocess.py path/to/transcript.vtt
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

VTT_TIMESTAMP_RE = re.compile(
    r"^\s*\d{1,2}:\d{2}(?::\d{2})?\.\d{1,3}\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?\.\d{1,3}.*$"
)
VTT_CUE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")
VTT_HEADER_RE = re.compile(r"^\s*(WEBVTT|NOTE|STYLE|REGION)\b.*$", re.IGNORECASE)
VTT_SPEAKER_TAG_RE = re.compile(r"<v\s+([^>]+)>([^<]*)</v>", re.IGNORECASE)
ANGLE_TAG_RE = re.compile(r"<[^>]+>")
SPEAKER_PREFIX_RE = re.compile(
    r"^([A-Za-z가-힣][A-Za-z0-9가-힣 _.\-]{0,40}?)\s*[:：]\s*(.*)$"
)

HANGUL_RE = re.compile(r"[가-힯]")


def _is_blank(line: str) -> bool:
    return not line.strip()


def parse_vtt(raw: str) -> tuple[list[tuple[str | None, str]], list[str]]:
    """Return (turns, speakers) where turns = list of (speaker_or_None, text)."""
    turns: list[tuple[str | None, str]] = []
    speakers_seen: list[str] = []

    for line in raw.splitlines():
        if _is_blank(line):
            continue
        if VTT_HEADER_RE.match(line):
            continue
        if VTT_TIMESTAMP_RE.match(line):
            continue
        if VTT_CUE_NUMBER_RE.match(line):
            continue

        speaker: str | None = None
        text = line

        m = VTT_SPEAKER_TAG_RE.search(line)
        if m:
            speaker = m.group(1).strip()
            text = VTT_SPEAKER_TAG_RE.sub(r"\2", line).strip()
        else:
            sp = SPEAKER_PREFIX_RE.match(line)
            if sp:
                speaker = sp.group(1).strip()
                text = sp.group(2).strip()

        text = ANGLE_TAG_RE.sub("", text).strip()
        if not text:
            continue

        if speaker and speaker not in speakers_seen:
            speakers_seen.append(speaker)
        turns.append((speaker, text))

    return turns, speakers_seen


def parse_plain(raw: str) -> tuple[list[tuple[str | None, str]], list[str]]:
    """Plain .txt / .md: treat `Speaker: text` lines as speaker turns."""
    turns: list[tuple[str | None, str]] = []
    speakers_seen: list[str] = []

    for line in raw.splitlines():
        line = line.rstrip()
        if _is_blank(line):
            continue
        if line.startswith("#"):
            turns.append((None, line))
            continue
        sp = SPEAKER_PREFIX_RE.match(line)
        if sp:
            speaker = sp.group(1).strip()
            text = sp.group(2).strip()
            if speaker not in speakers_seen:
                speakers_seen.append(speaker)
            turns.append((speaker, text))
        else:
            turns.append((None, line.strip()))

    return turns, speakers_seen


def merge_same_speaker(
    turns: list[tuple[str | None, str]],
) -> list[tuple[str | None, str]]:
    merged: list[tuple[str | None, str]] = []
    for speaker, text in turns:
        if merged and merged[-1][0] == speaker and speaker is not None:
            merged[-1] = (speaker, merged[-1][1] + " " + text)
        else:
            merged.append((speaker, text))
    return merged


def detect_language(text: str, filename: str) -> str:
    name = filename.lower()
    if ".en." in name:
        return "en"
    if ".ko." in name:
        return "ko"

    hangul_chars = len(HANGUL_RE.findall(text))
    non_ws = sum(1 for c in text if not c.isspace())
    if non_ws == 0:
        return "en"
    ratio = hangul_chars / non_ws
    return "ko" if ratio >= 0.20 else "en"


def render(turns: list[tuple[str | None, str]]) -> str:
    out: list[str] = []
    for speaker, text in turns:
        if speaker:
            out.append(f"{speaker}: {text}")
        else:
            out.append(text)
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: preprocess.py <transcript-path>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 1

    raw = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()

    if ext == ".vtt":
        turns, speakers = parse_vtt(raw)
    else:
        turns, speakers = parse_plain(raw)

    turns = merge_same_speaker(turns)
    cleaned = render(turns)
    lang = detect_language(cleaned, path.name)

    out = {
        "lang": lang,
        "text": cleaned,
        "speakers": speakers,
        "lines": len(turns),
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
