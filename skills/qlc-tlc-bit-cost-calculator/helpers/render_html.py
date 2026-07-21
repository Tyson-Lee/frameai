#!/usr/bin/env python3
"""Render sweep.json (or a blank/sample scaffold) into a self-contained
interactive HTML visualization.

No external JS/CSS dependencies (no CDN) so the file opens standalone from
disk or a Claude Code file preview. A range-slider input picks the QLC:TLC
mix ratio; SIX inline-SVG line charts redraw live:
  1. Bit 생산량 vs QLC 비율 (monthly, 억GB — basis picked by the "기준 시점"
     toggle, see below; mature yield by default)
  2. Cost/GB vs QLC 비율 (monthly, cent/GB — same "기준 시점" toggle)
  3. 5년 누적 Bit 생산량 vs QLC 비율 (억GB) — actual month-by-month sum over
     each line/recipe's OWN yield-ramp curve (see calc.py's
     cumulative_ramp_bit_per_wafer), not a flat monthly*months
     multiplication; production starts at month 1 (no development-months
     skip — see "ER period / t95" below)
  4. 5년 누적 Cost/GB vs QLC 비율 (cent/GB) — cost does not depend on yield,
     so this is still monthly wafer cost (dev cost excluded) times the full
     60-month window, plus the one-time dev cost added once, see calc.py's
     sweep()
  5. QLC 수율 램프업 (%, x축 = 생산 시작 후 경과 개월 0~36) — dedicated QLC
     line vs combo QLC recipe, FIXED reference curves independent of the
     ratio slider (see calc.py's yield_ramp_curve)
  6. TLC 수율 램프업 (%, x축 = 생산 시작 후 경과 개월 0~36) — dedicated TLC
     line vs combo TLC recipe, same fixed-reference treatment
Charts 1-4 each draw TWO solid lines side by side — combo and dedicated —
both swept over the same 0-100% ratio, though each line's wafer volume
comes from its OWN 100%-utilization max capa (the four lines' max
capacities are independent numbers, not shares of one fab-wide pool).
Charts 5-6 are NOT ratio-dependent (no vertical ratio indicator) — they are
tuning references for mature_yield/ramp_coef, always shown as-is.

"기준 시점" (yield basis) toggle — charts 1-2 AND the results table's
combo/dedicated "Bit 생산량"/"Cost / bit" cells ONLY: a radio choice between
"성숙 수율 기준" (default — identical to before, mature_yield used as-is) and
"특정 개월 기준" (a 1-60 month slider, styled like the QLC:TLC ratio slider).
In month mode, each of the four lines'/recipes' bit-per-wafer is recomputed
with that line's/recipe's OWN actual yield_ramp_fraction(mature_yield,
ramp_coef, t) at the chosen month t instead of the mature yield — wafer
counts and cost totals are untouched (cost never depended on yield), so only
bit totals and anything derived from them (cost/bit, cost/GB) move. This is
computed by a SEPARATE "display sweep" (`computeDisplaySweep`, mirrored from
calc.yield_ramp_progress_pct's underlying formula) layered on top of the
base `sweep` — every other output (wafer/월 rows, the 1-year/5-year
cumulative rows, the verdict text, dev-cost/ER/full-buildout notes, charts
3-6, and the crossover comparison baked into `sweep.json`/report.md) keeps
reading the base `sweep`, which stays mature-yield-only exactly as before;
this toggle cannot move them. When month mode is active, a note also shows
the chosen month and each line's/recipe's own ramp progress (% of ITS mature
yield reached at that month, independent of the mature yield value itself).

ER period / t95 (see calc.py module docstring for the full model): each of
the four lines/recipes reaches 95% of ITS OWN mature yield at its own t95 =
ln(20)/yield_ramp_coef months into its own production — that is its own
"ER(엔지니어링 런)/qualification period". `er_wafer_combo` /
`er_wafer_dedicated` are each a MONTHLY ER-wafer consumption RATE (not a
one-time total), applied independently to both of a scenario's two
lines/recipes during each one's own ER period — carved OUT of that line's/
recipe's normal wafer_total (never added on top of it). The 1-year/5-year
cumulative bit totals (charts 3-4's underlying data, plus the results
panel's new rows) therefore split into a TOTAL bit figure (unchanged
formula) and a NEW "판매용 bit 생산량" (sale-only) figure that nets out the
bit the ER-consumed wafers would have produced. The results panel's top
intro paragraph also shows, live, each scenario's current-ratio 1-year and
5-year TOTAL bit production (see "Dynamic intro stats" below).

The "전체 투자비용 (Max capa 풀 빌드아웃 기준)" figure is NOT a chart — it is
two ratio-independent numbers shown as plain text in the results panel
(see `full_buildout()` in calc.py), since it is a single flat total per
scenario rather than something that benefits from a line chart.

Every fab parameter calc.py requires (qlc_*/tlc_*/combo_*/er_wafer_*/
headcount/mask_count/coef_cost_* — see calc.REQUIRED_KEYS, including the
four independent max-capa fields and the eight yield fields split into
mature_yield/yield_ramp_coef pairs) is exposed as a number input, grouped by
line/recipe, alongside the currency_unit/bit_unit/ratio_step/
exchange_rate_krw_per_usd display settings and the cost-mode toggle (see
"Cost calculation modes" below). Editing ANY of them recomputes both
scenarios entirely client-side (the JS below mirrors calc.py's
bit_per_wafer / yield_fraction / yield_ramp_fraction / yield_ramp_t95 /
line_ramp_stats / cumulative_ramp_bit_per_wafer / capex_rate_per_wafer /
combo_dev_cost / dedicated_dev_cost / sweep / full_buildout formulas) — real
fab parameters never have to leave the browser in a params file. Required
fields that are empty or non-numeric are flagged inline and block
recomputation with an error banner instead of silently producing garbage
numbers.

Cost calculation modes: a "원가 계산 모드" radio toggle picks between
"모델 기반 계산" (model — capex/dev-cost model, the original behavior) and
"GB당 원가 직접 입력" (direct — bypass the model entirely and use two
directly-entered cent/GB numbers, `combo_direct_cost_per_gb` /
`dedicated_direct_cost_per_gb`, as flat ratio-independent values for the
Cost/GB charts). Selecting "direct" disables (greys out) every capex/
dev-cost input field (`calc.COST_MODEL_ONLY_KEYS` — capex_per_wafer x3,
headcount x2, mask_count x2, the two dev-cost coefficients) and those
fields are skipped by required-field validation entirely — they are not
used and do not block computation. `er_wafer_combo`/`er_wafer_dedicated` are
deliberately NOT in this list — they now feed the bit-production sale/ER
split (see "ER period / t95" above), which matters in BOTH cost modes, so
those two fields stay enabled and required regardless of `cost_mode`. Bit
production (and its two charts, 1 and 3) is ALWAYS computed from the
physical model (density/gross_die/yield-ramp/max_capa/ER split) regardless
of this toggle. In "direct" mode, the results panel's Total cost /
Cost-per-bit table cells and the one-time dev-cost / full-buildout text
lines are shown as "—" (not applicable) rather than a stale or fabricated
model-based number, and a note states which fields are being ignored.

Unit labels (see calc.py's module docstring for the full unit-conversion
rationale): `*_mature_yield` fields are a percentage (82 = 82%, the FULLY
RAMPED yield); `*_yield_ramp_coef` fields are a ramp-up speed (1/month);
`*_capex_per_wafer` fields are cost per 10,000 wafers; `*_density` fields
are Gb/Wafer; `*_max_capa` fields are wafer/월. Charts 1-4 convert the raw
Gb sweep data to GB at the display layer only (1 GB = 8 Gb): the
bit-production charts' y-axis is fixed at 억GB (10^8 GB); the cost charts'
y-axis is fixed at **cent/GB** (converted from the already-억원-denominated
cost/GB figure via the `exchange_rate_krw_per_usd` display setting when
cost_mode is "model" — see calc.py's `cost_per_gb_eokwon_to_cent`/
`WON_PER_EOKWON`/`CENT_PER_USD`, mirrored below by `costPerGbEokwonToCent()`
— or used AS-IS with no conversion when cost_mode is "direct", since those
inputs are already denominated in cent/GB). Both chart axes are also drawn
directly on the y-axis itself (rotated label + numeric ticks), not just in
the chart title, so neither axis ever reads as an arbitrary-unit line.

The page's initial values are embedded as a pretty-printed, per-key-commented
`var INITIAL_PAYLOAD = {...}` JS literal (see `_payload_js_literal`) instead
of a compact `<script type="application/json">` blob — this is deliberate so
that someone who opens `visualization.html` in a plain text editor (no
FrameAI, no Python) can find, read, and edit the "params" values (capex,
density, yield ramp, max capa, headcount/mask, coefficients, ...) directly,
save, and have those become the new initial values next time the file is
opened in a browser.

Dynamic intro stats: the top-of-page intro paragraph (`#introStats`) shows,
live, four numbers that update every time the ratio slider moves (or any
parameter changes) — 콤보 생산's current-ratio 1-year AND 5-year TOTAL bit
production, and 분리 생산's current-ratio 1-year AND 5-year TOTAL bit
production (all in 억GB) — so the strategic "how much do I actually make in
year 1 vs by year 5" question is visible without opening the results table.

Two buttons manage the field values:
  - "불러온 초기값으로 전체 재설정" — restores every field to the values the
    page was rendered with (sample data, a real params file, or blank).
  - "전체 비우기" — clears every fab-parameter field to empty, regardless of
    what the page was rendered with, for switching to real (non-exportable)
    fab numbers typed in by hand.

Three invocation modes:
    python3 render_html.py <sweep.json> <output_html_path>
        Seeds the page with a real calc.py run (params file was available).
        If sweep.json has "is_sample": true, a banner marks the page as
        pre-filled with sample/demo data rather than a real fab result.
    python3 render_html.py --blank <output_html_path>
        No params file/text existed and no sample was wanted. Produces the
        same page with every fab-parameter field blank.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calc  # noqa: E402

# UI grouping + Korean labels for calc.REQUIRED_KEYS. Order mirrors the
# grouping comments in calc.py (dedicated QLC / dedicated TLC / combo shared
# / combo QLC recipe / combo TLC recipe / one-time dev cost).
PARAM_GROUPS: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("dedicated-qlc", "QLC 전용 라인 (분리 생산)", [
        ("qlc_capex_per_wafer", "투자비 (capex, currency_unit/1만 Wafer) — GB당 원가 직접 입력 모드에서는 비활성화"),
        ("qlc_density", "Density (Gb/Wafer)"),
        ("qlc_gross_die", "Grossdie/Wafer"),
        ("qlc_mature_yield", "성숙 수율 (%, 완전히 램프업된 이후)"),
        ("qlc_yield_ramp_coef", "수율 램프업 속도 계수 (1/개월, 클수록 빨리 성숙 수율 도달)"),
        ("qlc_max_capa", "Max Wafer capa (QLC 전용 라인 100% 가동시, wafer/월)"),
    ]),
    ("dedicated-tlc", "TLC 전용 라인 (분리 생산)", [
        ("tlc_capex_per_wafer", "투자비 (capex, currency_unit/1만 Wafer) — GB당 원가 직접 입력 모드에서는 비활성화"),
        ("tlc_density", "Density (Gb/Wafer)"),
        ("tlc_gross_die", "Grossdie/Wafer"),
        ("tlc_mature_yield", "성숙 수율 (%, 완전히 램프업된 이후)"),
        ("tlc_yield_ramp_coef", "수율 램프업 속도 계수 (1/개월, 클수록 빨리 성숙 수율 도달)"),
        ("tlc_max_capa", "Max Wafer capa (TLC 전용 라인 100% 가동시, wafer/월)"),
    ]),
    ("combo-shared", "콤보 라인 공통 (QLC·TLC 레시피 공유)", [
        ("combo_capex_per_wafer", "투자비 (capex, currency_unit/1만 Wafer) — GB당 원가 직접 입력 모드에서는 비활성화"),
        ("combo_gross_die", "Grossdie/Wafer"),
    ]),
    ("combo-qlc", "콤보 — QLC 레시피", [
        ("combo_qlc_density", "Density (Gb/Wafer)"),
        ("combo_qlc_mature_yield", "성숙 수율 (%, 완전히 램프업된 이후)"),
        ("combo_qlc_yield_ramp_coef", "수율 램프업 속도 계수 (1/개월, 클수록 빨리 성숙 수율 도달)"),
        ("combo_qlc_max_capa", "Max Wafer capa (콤보가 QLC 레시피로 100% 가동시, wafer/월)"),
    ]),
    ("combo-tlc", "콤보 — TLC 레시피", [
        ("combo_tlc_density", "Density (Gb/Wafer)"),
        ("combo_tlc_mature_yield", "성숙 수율 (%, 완전히 램프업된 이후)"),
        ("combo_tlc_yield_ramp_coef", "수율 램프업 속도 계수 (1/개월, 클수록 빨리 성숙 수율 도달)"),
        ("combo_tlc_max_capa", "Max Wafer capa (콤보가 TLC 레시피로 100% 가동시, wafer/월)"),
    ]),
    ("er-wafer", "ER(엔지니어링 런) wafer 소모량 — 월간 소모 RATE, 원가 계산 모드와 무관하게 항상 bit 생산량(판매용/총량 split)에 반영", [
        ("er_wafer_combo", "월간 ER wafer 소모량 (콤보, wafer/월) — 콤보 QLC·TLC 레시피 각각 자기 ER 기간(t95) 동안 독립적으로 소모"),
        ("er_wafer_dedicated", "월간 ER wafer 소모량 (분리, wafer/월) — 분리 QLC·TLC 라인 각각 자기 ER 기간(t95) 동안 독립적으로 소모"),
    ]),
    ("dev-cost", "1회성 개발비 — 인력 / Mask 만 (ER wafer는 이제 bit 생산량 모델의 일부이므로 별도 그룹, GB당 원가 직접 입력 모드에서는 이 그룹 전부 비활성화)", [
        ("combo_headcount", "필요 인력 명 수 (콤보 개발시)"),
        ("dedicated_headcount", "필요 인력 명 수 (분리 개발시)"),
        ("combo_mask_count", "소모 Mask 매수 (콤보 개발시)"),
        ("dedicated_mask_count", "소모 Mask 매수 (분리 개발시)"),
        ("coef_cost_per_headcount", "인력 1명당 환산 비용 (콤보·분리 공통 계수, currency_unit/명)"),
        ("coef_cost_per_mask", "Mask 1매당 환산 비용 (콤보·분리 공통 계수, currency_unit/매)"),
    ]),
]

PARAM_LABELS: dict[str, str] = {
    key: label for _gid, _glabel, fields in PARAM_GROUPS for key, label in fields
}

assert set(PARAM_LABELS) == set(calc.REQUIRED_KEYS), (
    "PARAM_GROUPS in render_html.py must mirror calc.REQUIRED_KEYS exactly"
)

# Labels for the optional display-setting keys that also live in
# payload["params"] (calc.OPTIONAL_STR_DEFAULTS) but aren't part of
# PARAM_GROUPS since they're not fab parameters.
OPTIONAL_PARAM_LABELS: dict[str, str] = {
    "currency_unit": "비용 표시 단위 (자유 텍스트, 예: 억원/$M — 표의 Cost 행에만 쓰임. Cost 그래프 y축은 항상 cent/GB 고정)",
    "bit_unit": "bit 표시 단위 (자유 텍스트, 표의 Bit 생산량 행에만 쓰임 — 그래프 y축은 항상 GB 고정)",
    "ratio_step": "슬라이더 스윕 간격 % (1~100)",
    "exchange_rate_krw_per_usd": "환율 (원/달러) — Cost 그래프의 cent/GB 환산에만 쓰임 (cost_mode=model 일 때만; direct 모드에서는 미사용)",
    "cost_mode": "원가 계산 모드 (model=투자비/개발비 모델 기반 계산, direct=GB당 원가 직접 입력) — bit 생산량 계산에는 영향 없음",
    "combo_direct_cost_per_gb": "콤보 GB당 원가 직접 입력값 (cent/GB) — cost_mode=direct 일 때만 사용",
    "dedicated_direct_cost_per_gb": "분리 GB당 원가 직접 입력값 (cent/GB) — cost_mode=direct 일 때만 사용",
}

_PAYLOAD_COMMENT_LABELS: dict[str, str] = {**PARAM_LABELS, **OPTIONAL_PARAM_LABELS}
_PAYLOAD_LINE_RE = re.compile(r'^(\s*)"([a-zA-Z0-9_]+)":\s*(.*?)(,?)\s*$')


def _payload_js_literal(payload: dict) -> str:
    """Pretty-print `payload` as an indented JS object literal (not raw
    JSON) so it can be embedded as `var INITIAL_PAYLOAD = <this>;` — JS
    object literals allow trailing `//` comments, which plain JSON does
    not, so every key inside "params" gets its meaning + unit documented
    inline for someone editing the file in a plain text editor."""
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    lines = text.split("\n")

    start = next(i for i, ln in enumerate(lines) if ln.strip() == '"params": {')
    indent = len(lines[start]) - len(lines[start].lstrip(" "))
    end = next(
        i for i in range(start + 1, len(lines))
        if lines[i].strip() in ("}", "},")
        and (len(lines[i]) - len(lines[i].lstrip(" "))) == indent
    )
    for i in range(start + 1, end):
        m = _PAYLOAD_LINE_RE.match(lines[i])
        if not m:
            continue
        label = _PAYLOAD_COMMENT_LABELS.get(m.group(2))
        if label:
            lines[i] = lines[i] + "  // " + label
    return "\n".join(lines)


SAMPLE_BANNER_HTML = (
    '<div class="sample-banner" id="sampleBanner">샘플 데이터로 미리 채워졌습니다 — '
    "실제 fab 값을 입력하려면 아래 &quot;전체 비우기&quot; 버튼을 누르세요.</div>"
)

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QLC vs TLC bit-cost calculator</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280; --panel: #f4f5f7;
    --border: #d9dce1; --combo: #2563eb; --dedicated: #d97706;
    --danger: #dc2626;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #14161a; --fg: #e8e9eb; --muted: #9aa1ac; --panel: #1d2025;
      --border: #33373f; --combo: #6ea8fe; --dedicated: #f5a623;
      --danger: #f87171; }
  }
  body { font-family: -apple-system, "Segoe UI", Pretendard, sans-serif; background: var(--bg);
    color: var(--fg); margin: 0; padding: 24px; }
  h1 { font-size: 1.25rem; margin: 0 0 4px; }
  p.sub { color: var(--muted); margin: 0 0 20px; font-size: 0.9rem; }
  .sample-banner { margin: 0 0 16px; padding: 8px 12px; border-radius: 8px; font-size: 0.8rem;
    background: rgba(37, 99, 235, 0.08); border: 1px solid var(--combo); color: var(--fg); }
  .layout { display: grid; grid-template-columns: minmax(280px, 380px) 1fr; gap: 20px; align-items: start; }
  @media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  label { display: block; font-size: 0.85rem; color: var(--muted); margin-bottom: 6px; }
  input[type=range] { width: 100%; accent-color: var(--combo); }
  input[type=range]:disabled { opacity: 0.4; }
  .ratio-readout { font-size: 1.6rem; font-weight: 600; margin: 8px 0 16px; }
  .ratio-readout .qlc { color: var(--combo); } .ratio-readout .tlc { color: var(--dedicated); }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; }
  td { padding: 4px 0; border-bottom: 1px solid var(--border); }
  td.val { text-align: right; font-variant-numeric: tabular-nums; }
  .verdict { margin-top: 14px; padding: 10px 12px; border-radius: 8px; font-size: 0.85rem;
    background: var(--bg); border: 1px solid var(--border); min-height: 1.2em; }
  .dev-cost-note { margin-top: 10px; padding: 10px 12px; border-radius: 8px; font-size: 0.78rem;
    background: var(--bg); border: 1px solid var(--border); color: var(--muted); line-height: 1.5; }
  .error-banner { margin-top: 14px; padding: 10px 12px; border-radius: 8px; font-size: 0.82rem;
    background: rgba(220, 38, 38, 0.08); border: 1px solid var(--danger); color: var(--fg); }
  .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
    gap: 20px; align-content: start; align-items: start; }
  .chart-title { font-size: 0.85rem; color: var(--muted); margin: 0 0 6px; }
  .chart-placeholder { padding: 40px 16px; text-align: center; color: var(--muted);
    border: 1px dashed var(--border); border-radius: 10px; font-size: 0.9rem; }
  svg { width: 100%; height: auto; overflow: visible; }
  .axis-label { font-size: 10px; fill: var(--muted); }
  .axis-unit-label { font-size: 10px; fill: var(--fg); font-weight: 600; }
  .legend { display: flex; gap: 16px; font-size: 0.78rem; color: var(--muted); margin-top: 4px; }
  .legend span { display: inline-flex; align-items: center; gap: 5px; }
  .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
  .subpanel { margin-top: 20px; }
  .subpanel > label { margin-bottom: 4px; font-weight: 600; color: var(--fg); }
  .subpanel-hint { font-size: 0.78rem; color: var(--muted); margin: 0 0 10px; }
  .field-group { border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px 12px;
    margin: 0 0 10px; }
  .field-group legend { padding: 0 4px; font-size: 0.78rem; color: var(--muted); }
  .field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 12px; }
  .field label { margin-bottom: 3px; font-size: 0.78rem; }
  .field label code { font-size: 0.72rem; color: var(--muted); }
  .field input { width: 100%; box-sizing: border-box; padding: 5px 7px;
    border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--fg);
    font-variant-numeric: tabular-nums; }
  .field input.invalid { border-color: var(--danger); }
  .field input:disabled { opacity: 0.45; background: var(--panel); cursor: not-allowed; }
  .radio-label { display: flex; align-items: center; gap: 6px; font-size: 0.82rem;
    color: var(--fg); margin-bottom: 8px; cursor: pointer; }
  .radio-label input { width: auto; }
  .btn-row { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .reset-btn { font-size: 0.78rem; padding: 6px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: var(--bg); color: var(--fg); cursor: pointer; }
  .reset-btn:hover { background: var(--panel); }
</style>
</head>
<body>
<h1>QLC / TLC bit-cost 계산기</h1>
<p class="sub">모든 fab 파라미터를 이 화면에서 직접 입력할 수 있는 완전한
클라이언트사이드 계산기입니다 — 값은 서버로 전송되지 않고 브라우저 안에서만 계산됩니다.
슬라이더로 QLC:TLC 생산 비율을 조절하면, 각 라인이 자기 자신의 100% max capa를
기준으로 그 비율만큼만 가동한다고 보고 콤보와 분리 생산 두 시나리오의 bit 생산량과
bit당 비용이 실시간으로 나란히 갱신됩니다 (네 라인의 max capa는 서로 다른 값일 수
있으며 하나의 공유 풀이 아닙니다).</p>
<p class="sub" id="introStats"></p>
__SAMPLE_BANNER__
<div class="layout">
  <div class="panel">
    <label for="ratio">QLC:TLC 생산 비율</label>
    <input id="ratio" type="range" min="0" max="100" step="__STEP__" value="__DEFAULT__">
    <div class="ratio-readout"><span class="qlc" id="qlcPct"></span> : <span class="tlc" id="tlcPct"></span></div>

    <div class="subpanel" id="yieldBasisPanel">
      <label>기준 시점 (아래 Bit 생산량/Cost 그래프 2개 + 표의 Bit 생산량·Cost/bit 수치 전용)</label>
      <p class="subpanel-hint">5년/1년 누적, 수율 램프업 그래프, crossover 판정(아래 판정 문구)에는
      영향을 주지 않습니다 — 그 값들은 이 토글과 무관하게 항상 성숙 수율 기준입니다.</p>
      <label class="radio-label"><input type="radio" name="yieldBasis" id="yieldBasisMature" value="mature" checked> 성숙 수율 기준 (기본값)</label>
      <label class="radio-label"><input type="radio" name="yieldBasis" id="yieldBasisMonth" value="month"> 특정 개월 기준</label>
      <label for="basisMonth">기준 개월 (생산 시작 후 경과 개월)</label>
      <input id="basisMonth" type="range" min="1" max="60" step="1" value="12">
      <div class="ratio-readout" id="basisMonthReadout" style="font-size:1rem;margin:4px 0 8px;"></div>
      <div class="dev-cost-note" id="basisYieldNote"></div>
    </div>

    <table>
      <tr><td colspan="2" style="padding-top:10px;color:var(--muted)">콤보 생산</td></tr>
      <tr><td>Wafer/월 (QLC 레시피, combo_qlc_max_capa 기준)</td><td class="val" id="waferQlcCombo"></td></tr>
      <tr><td>Wafer/월 (TLC 레시피, combo_tlc_max_capa 기준)</td><td class="val" id="waferTlcCombo"></td></tr>
      <tr><td>Bit 생산량 (<span class="unit-bit"></span>)</td><td class="val" id="comboBit"></td></tr>
      <tr><td>Total cost (<span class="unit-currency"></span>, 개발비 포함)</td><td class="val" id="comboCost"></td></tr>
      <tr><td>Cost / bit</td><td class="val" id="comboCostPerBit"></td></tr>
      <tr><td>1년 누적 Bit 생산량 (총량/판매용, 억GB)</td><td class="val" id="comboOneYearBit"></td></tr>
      <tr><td>5년 누적 Bit 생산량 (총량/판매용, 억GB)</td><td class="val" id="comboFiveYearBit"></td></tr>
      <tr><td colspan="2" style="padding-top:10px;color:var(--muted)">분리 생산</td></tr>
      <tr><td>Wafer/월 (QLC 라인, qlc_max_capa 기준)</td><td class="val" id="waferQlcDed"></td></tr>
      <tr><td>Wafer/월 (TLC 라인, tlc_max_capa 기준)</td><td class="val" id="waferTlcDed"></td></tr>
      <tr><td>Bit 생산량 (<span class="unit-bit"></span>)</td><td class="val" id="dedBit"></td></tr>
      <tr><td>Total cost (<span class="unit-currency"></span>, 개발비 포함)</td><td class="val" id="dedCost"></td></tr>
      <tr><td>Cost / bit</td><td class="val" id="dedCostPerBit"></td></tr>
      <tr><td>1년 누적 Bit 생산량 (총량/판매용, 억GB)</td><td class="val" id="dedOneYearBit"></td></tr>
      <tr><td>5년 누적 Bit 생산량 (총량/판매용, 억GB)</td><td class="val" id="dedFiveYearBit"></td></tr>
    </table>
    <div class="verdict" id="verdict"></div>
    <div class="dev-cost-note" id="devCostNote"></div>
    <div class="dev-cost-note" id="erInfoNote"></div>
    <div class="dev-cost-note" id="fullBuildoutNote"></div>
    <div class="error-banner" id="paramErrors" role="alert" style="display:none"></div>

    <div class="subpanel" id="costModePanel">
      <label>원가 계산 모드</label>
      <p class="subpanel-hint">"GB당 원가 직접 입력"을 고르면 투자비/개발비 입력은
      비활성화되고 계산에 쓰이지 않습니다. bit 생산량 계산(및 그 그래프)은 이 모드와
      무관하게 항상 물리 모델(density/gross_die/수율/max capa)을 사용합니다.</p>
      <label class="radio-label"><input type="radio" name="costMode" id="costModeModel" value="model"> 모델 기반 계산 (투자비/density/수율/개발비 등 반영)</label>
      <label class="radio-label"><input type="radio" name="costMode" id="costModeDirect" value="direct"> GB당 원가 직접 입력 (cent/GB)</label>
      <div class="field-grid" id="directCostFields">
        <div class="field">
          <label for="comboDirectCostInput">콤보 GB당 원가 <code>combo_direct_cost_per_gb</code> (cent/GB)</label>
          <input id="comboDirectCostInput" type="number" step="any" min="0" inputmode="decimal">
        </div>
        <div class="field">
          <label for="dedicatedDirectCostInput">분리 GB당 원가 <code>dedicated_direct_cost_per_gb</code> (cent/GB)</label>
          <input id="dedicatedDirectCostInput" type="number" step="any" min="0" inputmode="decimal">
        </div>
      </div>
    </div>

    <div class="subpanel" id="paramsPanel">
      <label>파라미터 입력 (fab 파라미터)</label>
      <p class="subpanel-hint">외부로 반출할 수 없는 실제 fab 수치를 이 화면에서 바로
      입력하세요. 비워두면 sweep이 계산되지 않고 위에 어떤 값이 비었는지 표시됩니다.</p>
      __PARAM_FIELDS__
    </div>

    <div class="subpanel" id="displayPanel">
      <label>표시 설정</label>
      <div class="field-grid">
        <div class="field">
          <label for="currencyUnitInput">비용 단위 (currency_unit)</label>
          <input id="currencyUnitInput" type="text">
        </div>
        <div class="field">
          <label for="bitUnitInput">bit 단위 (bit_unit)</label>
          <input id="bitUnitInput" type="text">
        </div>
        <div class="field">
          <label for="ratioStepInput">슬라이더 스윕 간격 % (ratio_step)</label>
          <input id="ratioStepInput" type="number" min="1" max="100" step="1">
        </div>
        <div class="field">
          <label for="exchangeRateInput">환율 (원/달러, exchange_rate_krw_per_usd) — Cost 그래프 cent/GB 환산 전용 (model 모드에서만 사용)</label>
          <input id="exchangeRateInput" type="number" min="1" step="any">
        </div>
      </div>
    </div>

    <div class="btn-row">
      <button class="reset-btn" id="resetAll" type="button">불러온 초기값으로 전체 재설정</button>
      <button class="reset-btn" id="clearAll" type="button">전체 비우기</button>
    </div>
  </div>
  <div class="charts">
    <div class="chart-placeholder" id="chartPlaceholder">모든 파라미터를 올바르게 입력하면 차트가 표시됩니다.</div>
    <div class="panel">
      <p class="chart-title" id="chartBitTitle">Bit 생산량 vs QLC 비율 (억GB)</p>
      <svg id="chartBit" viewBox="0 0 640 220" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="legend">
        <span><i class="swatch" style="background:var(--combo)"></i>콤보</span>
        <span><i class="swatch" style="background:var(--dedicated)"></i>분리 생산</span>
      </div>
    </div>
    <div class="panel">
      <p class="chart-title" id="chartCostTitle">Cost / GB vs QLC 비율 (cent/GB, 낮을수록 유리)</p>
      <svg id="chartCost" viewBox="0 0 640 220" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="legend">
        <span><i class="swatch" style="background:var(--combo)"></i>콤보</span>
        <span><i class="swatch" style="background:var(--dedicated)"></i>분리 생산</span>
      </div>
    </div>
    <div class="panel">
      <p class="chart-title" id="chartFiveYearBitTitle">5년 누적 Bit 생산량 vs QLC 비율 (억GB, 1개월차부터 각 라인/레시피가 자기 수율 램프업 곡선을 따라 실제 생산, 총량 기준)</p>
      <svg id="chartFiveYearBit" viewBox="0 0 640 220" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="legend">
        <span><i class="swatch" style="background:var(--combo)"></i>콤보</span>
        <span><i class="swatch" style="background:var(--dedicated)"></i>분리 생산</span>
      </div>
    </div>
    <div class="panel">
      <p class="chart-title" id="chartFiveYearCostTitle">5년 누적 Cost/GB vs QLC 비율 (cent/GB, 낮을수록 유리, 1회성 개발비 1회 포함)</p>
      <svg id="chartFiveYearCost" viewBox="0 0 640 220" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="legend">
        <span><i class="swatch" style="background:var(--combo)"></i>콤보</span>
        <span><i class="swatch" style="background:var(--dedicated)"></i>분리 생산</span>
      </div>
    </div>
    <div class="panel">
      <p class="chart-title">QLC 수율 램프업 (%, x축 = 생산 시작 후 경과 개월) — QLC:TLC 비율과 무관한 고정 참고용</p>
      <svg id="chartYieldRampQlc" viewBox="0 0 640 220" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="legend">
        <span><i class="swatch" style="background:var(--dedicated)"></i>분리 QLC 전용 라인</span>
        <span><i class="swatch" style="background:var(--combo)"></i>콤보 QLC 레시피</span>
      </div>
    </div>
    <div class="panel">
      <p class="chart-title">TLC 수율 램프업 (%, x축 = 생산 시작 후 경과 개월) — QLC:TLC 비율과 무관한 고정 참고용</p>
      <svg id="chartYieldRampTlc" viewBox="0 0 640 220" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="legend">
        <span><i class="swatch" style="background:var(--dedicated)"></i>분리 TLC 전용 라인</span>
        <span><i class="swatch" style="background:var(--combo)"></i>콤보 TLC 레시피</span>
      </div>
    </div>
  </div>
</div>

<!--
  이 파일을 텍스트 에디터(메모장 등)로 열었다면: 아래 INITIAL_PAYLOAD 의
  "params" 블록 안에 있는 숫자(또는 currency_unit/bit_unit/cost_mode 등
  문자열)를 직접 고친 뒤 저장하고, 이 html 파일을 다시 열면 그 값이
  초기값(입력창 기본값)으로 반영됩니다. 각 줄 끝의 "// 설명"은 그 파라미터의
  뜻과 단위를 적어둔 주석입니다 — 값만 바꾸고 줄의 따옴표(")와 콤마(,) 구조는
  그대로 두세요. "params" 아래의 sweep/crossover/dev_cost/best_* 항목은 이
  파일을 만들 때 계산했던 결과를 참고용으로 남겨둔 것일 뿐입니다 — 브라우저에서
  열리면 화면은 이 값을 다시 읽지 않고 항상 params 값으로부터 새로 계산하므로,
  그 항목들을 고쳐도 계산 결과에는 아무 영향이 없습니다.
-->
<script id="payload">
var INITIAL_PAYLOAD = __PAYLOAD_JS__;
</script>
<script>
(function () {
  var data = INITIAL_PAYLOAD;
  var REQUIRED_KEYS = __REQUIRED_KEYS_JSON__;
  var PARAM_LABELS = __PARAM_LABELS_JSON__;
  var COST_MODEL_ONLY_KEYS = __COST_MODEL_ONLY_KEYS_JSON__;
  var RAMP_CHART_MONTHS = __RAMP_CHART_MONTHS_JSON__;

  var initialParams = data.params || {};

  var slider = document.getElementById("ratio");
  var chartPlaceholder = document.getElementById("chartPlaceholder");
  var errorBanner = document.getElementById("paramErrors");

  var paramInputs = {};
  REQUIRED_KEYS.forEach(function (key) {
    paramInputs[key] = document.getElementById("param_" + key);
  });
  var currencyUnitInput = document.getElementById("currencyUnitInput");
  var bitUnitInput = document.getElementById("bitUnitInput");
  var ratioStepInput = document.getElementById("ratioStepInput");
  var exchangeRateInput = document.getElementById("exchangeRateInput");
  var costModeModelRadio = document.getElementById("costModeModel");
  var costModeDirectRadio = document.getElementById("costModeDirect");
  var comboDirectCostInput = document.getElementById("comboDirectCostInput");
  var dedicatedDirectCostInput = document.getElementById("dedicatedDirectCostInput");
  var directCostFieldsEl = document.getElementById("directCostFields");
  var yieldBasisMatureRadio = document.getElementById("yieldBasisMature");
  var yieldBasisMonthRadio = document.getElementById("yieldBasisMonth");
  var basisMonthSlider = document.getElementById("basisMonth");
  var basisMonthReadoutEl = document.getElementById("basisMonthReadout");
  var basisYieldNoteEl = document.getElementById("basisYieldNote");
  var chartBitTitleEl = document.getElementById("chartBitTitle");
  var chartCostTitleEl = document.getElementById("chartCostTitle");

  function resetAllInputs() {
    REQUIRED_KEYS.forEach(function (key) {
      var v = initialParams[key];
      paramInputs[key].value = (v === undefined || v === null || v === "") ? "" : v;
      paramInputs[key].classList.remove("invalid");
    });
    currencyUnitInput.value = data.currency_unit || "cost unit";
    bitUnitInput.value = data.bit_unit || "bit unit";
    ratioStepInput.value = initialParams.ratio_step || "5";
    exchangeRateInput.value = initialParams.exchange_rate_krw_per_usd || "1300";
    var initialCostMode = initialParams.cost_mode || "model";
    costModeDirectRadio.checked = initialCostMode === "direct";
    costModeModelRadio.checked = initialCostMode !== "direct";
    comboDirectCostInput.value = initialParams.combo_direct_cost_per_gb || "0";
    dedicatedDirectCostInput.value = initialParams.dedicated_direct_cost_per_gb || "0";
    updateCostModeUI();
  }

  function clearAllInputs() {
    REQUIRED_KEYS.forEach(function (key) {
      paramInputs[key].value = "";
      paramInputs[key].classList.remove("invalid");
    });
  }

  // Mirrors calc.py's bit_per_wafer / yield_fraction / yield_ramp_fraction /
  // yield_ramp_t95 / line_ramp_stats / capex_rate_per_wafer / bit_total_gb /
  // combo_dev_cost / dedicated_dev_cost / sweep / cumulative_ramp_bit_per_wafer
  // exactly -- keep these in sync if calc.py's formulas change.
  var GB_PER_GIGABIT = 8;          // 1 GB = 8 Gb (display/output layer only)
  var WAFER_BATCH_FOR_CAPEX = 10000; // capex_per_wafer is entered per 10K wafers
  var WON_PER_EOKWON = 100000000;  // 1 억원 = 100,000,000 원 (Cost chart cent/GB only)
  var CENT_PER_USD = 100;
  var ONE_YEAR_MONTHS = 12;        // 1-year cumulative window, in months
  var FIVE_YEAR_MONTHS = 60;       // 5-year cumulative window, in months -- both
                                    // windows start at production month 1, no
                                    // shared "development months" skip anymore
                                    // (see calc.py module docstring / t95 below).
  function bitPerWafer(density, grossDie, yieldVal) {
    return density * grossDie * yieldVal;
  }
  function yieldFraction(yieldPct) {
    return yieldPct / 100;
  }
  // Mirrors calc.yield_ramp_fraction -- Normalized Exponential Saturation.
  // t = months elapsed since THIS line/recipe's own production start.
  function yieldRampFraction(matureYieldPct, rampCoef, t) {
    return yieldFraction(matureYieldPct) * (1 - Math.exp(-rampCoef * t));
  }
  // Mirrors calc.yield_ramp_t95 -- months until this line's/recipe's own
  // yield reaches 95% of ITS OWN mature yield (independent of the mature
  // yield value itself); t=0..t95 is that line's/recipe's own ER period.
  function yieldRampT95(rampCoef) {
    return Math.log(20) / rampCoef;
  }
  // Mirrors calc.yield_ramp_progress_pct -- % of mature yield reached at
  // month t, independent of the mature yield value itself. Used ONLY by the
  // "기준 시점" toggle's reference note (never by the base sweep/crossover).
  function rampProgressPct(rampCoef, t) {
    return yieldRampFraction(100, rampCoef, t) * 100;
  }
  // Mirrors calc.cumulative_ramp_bit_per_wafer -- actual month-by-month sum
  // of bit-per-wafer over production months t=1..active_months, instead of
  // a flat monthly_bit_total * active_months multiplication.
  function cumulativeRampBitPerWafer(matureYieldPct, rampCoef, density, grossDie, activeMonths) {
    var months = Math.round(activeMonths);
    var total = 0;
    for (var t = 1; t <= months; t++) {
      total += density * grossDie * yieldRampFraction(matureYieldPct, rampCoef, t);
    }
    return total;
  }
  function capexRatePerWafer(capexPer10kWafer) {
    return capexPer10kWafer / WAFER_BATCH_FOR_CAPEX;
  }
  function bitTotalGb(bitTotal) {
    return bitTotal / GB_PER_GIGABIT;
  }
  // Mirrors calc.cost_per_gb_eokwon_to_cent -- Cost chart y-axis ONLY, and
  // ONLY used in cost_mode == "model" (direct-mode inputs are already
  // cent/GB, see chartPointsFromSweep). Assumes costPerGbEokwon is already
  // a plain numeric 억원 amount.
  function costPerGbEokwonToCent(costPerGbEokwon, exchangeRate) {
    if (!(exchangeRate > 0)) return Infinity;
    var usdPerGb = costPerGbEokwon * WON_PER_EOKWON / exchangeRate;
    return usdPerGb * CENT_PER_USD;
  }
  // One-time dev cost is headcount + mask ONLY -- the old ER-wafer cost term
  // is gone (wafer_total * capex_rate_per_wafer, unchanged, already pays for
  // every wafer processed, ER or not -- see calc.py module docstring).
  function comboDevCost(params) {
    return params.combo_headcount * params.coef_cost_per_headcount
      + params.combo_mask_count * params.coef_cost_per_mask;
  }
  function dedicatedDevCost(params) {
    return params.dedicated_headcount * params.coef_cost_per_headcount
      + params.dedicated_mask_count * params.coef_cost_per_mask;
  }
  // Mirrors calc.line_ramp_stats -- precomputes this line's/recipe's own
  // t95 and its cumulative bit-per-wafer over both cumulative windows, full
  // window and ER-period-only, so sweep rows need only one multiply/subtract
  // per window instead of a month-by-month loop per ratio.
  function lineRampStats(matureYieldPct, rampCoef, density, grossDie) {
    var t95 = yieldRampT95(rampCoef);
    return {
      t95: t95,
      bpw1y: cumulativeRampBitPerWafer(matureYieldPct, rampCoef, density, grossDie, ONE_YEAR_MONTHS),
      bpw5y: cumulativeRampBitPerWafer(matureYieldPct, rampCoef, density, grossDie, FIVE_YEAR_MONTHS),
      bpwEr1y: cumulativeRampBitPerWafer(matureYieldPct, rampCoef, density, grossDie, Math.min(t95, ONE_YEAR_MONTHS)),
      bpwEr5y: cumulativeRampBitPerWafer(matureYieldPct, rampCoef, density, grossDie, Math.min(t95, FIVE_YEAR_MONTHS)),
    };
  }
  // Mirrors calc.sweep's window_totals -- total bit (unchanged formula) and
  // sale-only bit (total minus the bit the ER-consumed wafers would have
  // produced) for one scenario over one cumulative window ("1y" or "5y"),
  // summing the QLC-recipe/line and TLC-recipe/line contributions.
  function windowTotals(waferQlc, waferTlc, erRate, statsQlc, statsTlc, windowKey) {
    var bpwKey = "bpw" + windowKey, bpwErKey = "bpwEr" + windowKey;
    var qlcTotal = waferQlc * statsQlc[bpwKey];
    var tlcTotal = waferTlc * statsTlc[bpwKey];
    var qlcErWafers = Math.min(erRate, waferQlc);
    var tlcErWafers = Math.min(erRate, waferTlc);
    var qlcSale = qlcTotal - qlcErWafers * statsQlc[bpwErKey];
    var tlcSale = tlcTotal - tlcErWafers * statsTlc[bpwErKey];
    return { total: qlcTotal + tlcTotal, sale: qlcSale + tlcSale };
  }
  // Mirrors calc.full_buildout -- ratio-independent total investment if each
  // scenario built every one of its lines out to its own 100%-utilization
  // max capacity. combo is one physical line, represented by
  // combo_qlc_max_capa (see calc.COMBO_FULL_CAPEX_ASSUMPTION / README /
  // report.md for why). Only meaningful in cost_mode == "model" -- shown as
  // TEXT (fullBuildoutNote), not a chart.
  function fullBuildout(params) {
    var dedicated = capexRatePerWafer(params.qlc_capex_per_wafer) * params.qlc_max_capa
      + capexRatePerWafer(params.tlc_capex_per_wafer) * params.tlc_max_capa
      + dedicatedDevCost(params);
    var combo = capexRatePerWafer(params.combo_capex_per_wafer) * params.combo_qlc_max_capa
      + comboDevCost(params);
    return { combo: combo, dedicated: dedicated };
  }
  function computeSweep(params, ratioStep) {
    var bpwComboQlc = bitPerWafer(params.combo_qlc_density, params.combo_gross_die, yieldFraction(params.combo_qlc_mature_yield));
    var bpwComboTlc = bitPerWafer(params.combo_tlc_density, params.combo_gross_die, yieldFraction(params.combo_tlc_mature_yield));
    var bpwDedQlc = bitPerWafer(params.qlc_density, params.qlc_gross_die, yieldFraction(params.qlc_mature_yield));
    var bpwDedTlc = bitPerWafer(params.tlc_density, params.tlc_gross_die, yieldFraction(params.tlc_mature_yield));
    var comboDev = comboDevCost(params);
    var dedDev = dedicatedDevCost(params);

    // Per-line/recipe ramp stats (t95 + cumulative bit-per-wafer over both
    // cumulative windows) -- independent of the ratio, computed once and
    // reused across every row below.
    var statsComboQlc = lineRampStats(params.combo_qlc_mature_yield, params.combo_qlc_yield_ramp_coef, params.combo_qlc_density, params.combo_gross_die);
    var statsComboTlc = lineRampStats(params.combo_tlc_mature_yield, params.combo_tlc_yield_ramp_coef, params.combo_tlc_density, params.combo_gross_die);
    var statsDedQlc = lineRampStats(params.qlc_mature_yield, params.qlc_yield_ramp_coef, params.qlc_density, params.qlc_gross_die);
    var statsDedTlc = lineRampStats(params.tlc_mature_yield, params.tlc_yield_ramp_coef, params.tlc_density, params.tlc_gross_die);

    function rowAt(r) {
      var qlcShare = r / 100, tlcShare = (100 - r) / 100;
      // Each line sweeps ITS OWN 100%-utilization max capa by the ratio --
      // not a shared fab-wide pool. wafer_total never changes because of ER
      // wafers -- they're carved OUT of it, not added on top.
      var waferQlcDed = params.qlc_max_capa * qlcShare;
      var waferTlcDed = params.tlc_max_capa * tlcShare;
      var waferQlcCombo = params.combo_qlc_max_capa * qlcShare;
      var waferTlcCombo = params.combo_tlc_max_capa * tlcShare;
      var comboBit = waferQlcCombo * bpwComboQlc + waferTlcCombo * bpwComboTlc;
      var comboCost = capexRatePerWafer(params.combo_capex_per_wafer) * (waferQlcCombo + waferTlcCombo) + comboDev;
      var dedBit = waferQlcDed * bpwDedQlc + waferTlcDed * bpwDedTlc;
      var dedCost = capexRatePerWafer(params.qlc_capex_per_wafer) * waferQlcDed
        + capexRatePerWafer(params.tlc_capex_per_wafer) * waferTlcDed + dedDev;
      var comboBitGb = bitTotalGb(comboBit);
      var dedBitGb = bitTotalGb(dedBit);

      // Cumulative (1-year/5-year) fields. Cost does not depend on yield
      // (paid per wafer processed), so it's a flat monthly rate times the
      // FULL window length (no development-months skip anymore) + dev_cost
      // added ONCE. Bit DOES depend on yield, which ramps up over time, so
      // it's the actual month-by-month sum (via windowTotals/lineRampStats
      // above) -- both a TOTAL figure (unchanged formula) and a sale-only
      // figure that nets out each line's/recipe's own ER wafer consumption.
      var comboMonthlyWaferCost = comboCost - comboDev;
      var dedMonthlyWaferCost = dedCost - dedDev;

      var fiveYearCombo = windowTotals(waferQlcCombo, waferTlcCombo, params.er_wafer_combo, statsComboQlc, statsComboTlc, "5y");
      var oneYearCombo = windowTotals(waferQlcCombo, waferTlcCombo, params.er_wafer_combo, statsComboQlc, statsComboTlc, "1y");
      var fiveYearDed = windowTotals(waferQlcDed, waferTlcDed, params.er_wafer_dedicated, statsDedQlc, statsDedTlc, "5y");
      var oneYearDed = windowTotals(waferQlcDed, waferTlcDed, params.er_wafer_dedicated, statsDedQlc, statsDedTlc, "1y");

      var fiveYearComboCost = comboMonthlyWaferCost * FIVE_YEAR_MONTHS + comboDev;
      var oneYearComboCost = comboMonthlyWaferCost * ONE_YEAR_MONTHS + comboDev;
      var fiveYearDedCost = dedMonthlyWaferCost * FIVE_YEAR_MONTHS + dedDev;
      var oneYearDedCost = dedMonthlyWaferCost * ONE_YEAR_MONTHS + dedDev;

      return {
        qlc_ratio: r, tlc_ratio: 100 - r,
        wafer_qlc_dedicated: waferQlcDed, wafer_tlc_dedicated: waferTlcDed,
        wafer_qlc_combo: waferQlcCombo, wafer_tlc_combo: waferTlcCombo,
        combo_bit_total: comboBit, combo_cost_total: comboCost,
        combo_cost_per_bit: comboBit > 0 ? comboCost / comboBit : Infinity,
        dedicated_bit_total: dedBit, dedicated_cost_total: dedCost,
        dedicated_cost_per_bit: dedBit > 0 ? dedCost / dedBit : Infinity,
        combo_bit_total_gb: comboBitGb, dedicated_bit_total_gb: dedBitGb,
        combo_cost_per_gb: comboBitGb > 0 ? comboCost / comboBitGb : Infinity,
        dedicated_cost_per_gb: dedBitGb > 0 ? dedCost / dedBitGb : Infinity,
        five_year_combo_bit_total: fiveYearCombo.total,
        five_year_combo_bit_total_gb: bitTotalGb(fiveYearCombo.total),
        five_year_combo_sale_bit_total: fiveYearCombo.sale,
        five_year_combo_sale_bit_total_gb: bitTotalGb(fiveYearCombo.sale),
        five_year_combo_cost_total: fiveYearComboCost,
        five_year_combo_cost_per_bit: fiveYearCombo.total > 0 ? fiveYearComboCost / fiveYearCombo.total : Infinity,
        five_year_combo_cost_per_gb: bitTotalGb(fiveYearCombo.total) > 0 ? fiveYearComboCost / bitTotalGb(fiveYearCombo.total) : Infinity,
        five_year_dedicated_bit_total: fiveYearDed.total,
        five_year_dedicated_bit_total_gb: bitTotalGb(fiveYearDed.total),
        five_year_dedicated_sale_bit_total: fiveYearDed.sale,
        five_year_dedicated_sale_bit_total_gb: bitTotalGb(fiveYearDed.sale),
        five_year_dedicated_cost_total: fiveYearDedCost,
        five_year_dedicated_cost_per_bit: fiveYearDed.total > 0 ? fiveYearDedCost / fiveYearDed.total : Infinity,
        five_year_dedicated_cost_per_gb: bitTotalGb(fiveYearDed.total) > 0 ? fiveYearDedCost / bitTotalGb(fiveYearDed.total) : Infinity,
        one_year_combo_bit_total: oneYearCombo.total,
        one_year_combo_bit_total_gb: bitTotalGb(oneYearCombo.total),
        one_year_combo_sale_bit_total: oneYearCombo.sale,
        one_year_combo_sale_bit_total_gb: bitTotalGb(oneYearCombo.sale),
        one_year_combo_cost_total: oneYearComboCost,
        one_year_combo_cost_per_bit: oneYearCombo.total > 0 ? oneYearComboCost / oneYearCombo.total : Infinity,
        one_year_combo_cost_per_gb: bitTotalGb(oneYearCombo.total) > 0 ? oneYearComboCost / bitTotalGb(oneYearCombo.total) : Infinity,
        one_year_dedicated_bit_total: oneYearDed.total,
        one_year_dedicated_bit_total_gb: bitTotalGb(oneYearDed.total),
        one_year_dedicated_sale_bit_total: oneYearDed.sale,
        one_year_dedicated_sale_bit_total_gb: bitTotalGb(oneYearDed.sale),
        one_year_dedicated_cost_total: oneYearDedCost,
        one_year_dedicated_cost_per_bit: oneYearDed.total > 0 ? oneYearDedCost / oneYearDed.total : Infinity,
        one_year_dedicated_cost_per_gb: bitTotalGb(oneYearDed.total) > 0 ? oneYearDedCost / bitTotalGb(oneYearDed.total) : Infinity,
      };
    }
    var rows = [], r = 0;
    while (r <= 100) { rows.push(rowAt(r)); r += ratioStep; }
    if (rows[rows.length - 1].qlc_ratio !== 100) rows.push(rowAt(100));
    return { rows: rows, comboDev: comboDev, dedDev: dedDev };
  }

  // Mirrors calc.yield_ramp_fraction, chosen either as the mature yield
  // (default) or the actual ramped yield at a specific month -- feeds ONLY
  // computeDisplaySweep below (charts 1-2 + the table's Bit 생산량/Cost per
  // bit cells), never the base sweep()/computeSweep above.
  function yieldFractionAtBasis(matureYieldPct, rampCoef, mode, months) {
    return mode === "month" ? yieldRampFraction(matureYieldPct, rampCoef, months) : yieldFraction(matureYieldPct);
  }
  // Recomputes ONLY the monthly Bit/Cost-per-bit/Cost-per-GB figures using
  // the chosen yield basis -- wafer counts and cost totals are reused as-is
  // from baseRows (cost never depends on yield), only bit_per_wafer (and
  // everything derived from it) changes. baseRows is always the base
  // "sweep" array (mature-yield, ratio-ordered) so the two arrays share the
  // same length/qlc_ratio order and can be indexed together.
  function computeDisplaySweep(params, baseRows, mode, months) {
    var yComboQlc = yieldFractionAtBasis(params.combo_qlc_mature_yield, params.combo_qlc_yield_ramp_coef, mode, months);
    var yComboTlc = yieldFractionAtBasis(params.combo_tlc_mature_yield, params.combo_tlc_yield_ramp_coef, mode, months);
    var yDedQlc = yieldFractionAtBasis(params.qlc_mature_yield, params.qlc_yield_ramp_coef, mode, months);
    var yDedTlc = yieldFractionAtBasis(params.tlc_mature_yield, params.tlc_yield_ramp_coef, mode, months);
    var bpwComboQlc = bitPerWafer(params.combo_qlc_density, params.combo_gross_die, yComboQlc);
    var bpwComboTlc = bitPerWafer(params.combo_tlc_density, params.combo_gross_die, yComboTlc);
    var bpwDedQlc = bitPerWafer(params.qlc_density, params.qlc_gross_die, yDedQlc);
    var bpwDedTlc = bitPerWafer(params.tlc_density, params.tlc_gross_die, yDedTlc);
    return baseRows.map(function (row) {
      var comboBit = row.wafer_qlc_combo * bpwComboQlc + row.wafer_tlc_combo * bpwComboTlc;
      var dedBit = row.wafer_qlc_dedicated * bpwDedQlc + row.wafer_tlc_dedicated * bpwDedTlc;
      var comboBitGb = bitTotalGb(comboBit);
      var dedBitGb = bitTotalGb(dedBit);
      return {
        qlc_ratio: row.qlc_ratio,
        combo_bit_total: comboBit,
        dedicated_bit_total: dedBit,
        combo_bit_total_gb: comboBitGb,
        dedicated_bit_total_gb: dedBitGb,
        combo_cost_per_bit: comboBit > 0 ? row.combo_cost_total / comboBit : Infinity,
        dedicated_cost_per_bit: dedBit > 0 ? row.dedicated_cost_total / dedBit : Infinity,
        combo_cost_per_gb: comboBitGb > 0 ? row.combo_cost_total / comboBitGb : Infinity,
        dedicated_cost_per_gb: dedBitGb > 0 ? row.dedicated_cost_total / dedBitGb : Infinity,
      };
    });
  }
  // Chart-point mapper for charts 1-2 ONLY (the ones the "기준 시점" toggle
  // affects) -- unlike chartPointsFromSweep below, this never touches
  // five_year_* fields, since the toggle must never reach the 5-year charts.
  function displayChartPointsFromSweep(rows, exchangeRate, costMode, directCostCent) {
    return rows.map(function (r) {
      var comboCostCent, dedCostCent;
      if (costMode === "direct") {
        comboCostCent = directCostCent.combo;
        dedCostCent = directCostCent.dedicated;
      } else {
        comboCostCent = costPerGbEokwonToCent(r.combo_cost_per_gb, exchangeRate);
        dedCostCent = costPerGbEokwonToCent(r.dedicated_cost_per_gb, exchangeRate);
      }
      return {
        qlc_ratio: r.qlc_ratio,
        combo_bit_100m_gb: r.combo_bit_total_gb / 1e8,
        dedicated_bit_100m_gb: r.dedicated_bit_total_gb / 1e8,
        combo_cost_per_gb_cent: comboCostCent,
        dedicated_cost_per_gb_cent: dedCostCent,
      };
    });
  }
  function currentYieldBasisMode() {
    return yieldBasisMonthRadio.checked ? "month" : "mature";
  }
  function currentYieldBasisMonths() {
    return Number(basisMonthSlider.value);
  }
  function updateBasisModeUI() {
    basisMonthSlider.disabled = currentYieldBasisMode() !== "month";
  }

  var sweep = [], comboDev = 0, dedDev = 0;
  var buildout = { combo: 0, dedicated: 0 };
  var currentParams = {};
  var currentCostMode = "model";
  var currentDirectCosts = { combo: 0, dedicated: 0 };

  function fmt(n) {
    if (!isFinite(n)) return "-";
    return n.toLocaleString(undefined, { maximumFractionDigits: n < 1 ? 6 : 0 });
  }

  function nearestRowIndex(rows, ratio) {
    var bestIdx = 0, bestDiff = Infinity;
    for (var i = 0; i < rows.length; i++) {
      var d = Math.abs(rows[i].qlc_ratio - ratio);
      if (d < bestDiff) { bestDiff = d; bestIdx = i; }
    }
    return bestIdx;
  }

  function escapeXml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function fmtAxisTick(v) {
    if (!isFinite(v)) return "-";
    if (v === 0) return "0";
    var abs = Math.abs(v);
    var digits = abs < 1 ? 3 : abs < 100 ? 1 : 0;
    return Number(v.toFixed(digits)).toLocaleString();
  }

  // yAxisUnit is drawn directly on the axis (rotated label + numeric ticks)
  // so the chart never reads as an arbitrary-unit line. xOpts generalizes
  // the x-axis: {key, min, max, ticks, tickFormat} -- defaults to the
  // original qlc_ratio 0-100% behavior when omitted (charts 1-4); the
  // yield-ramp charts (5-6) pass key:"month", min:0, max:RAMP_CHART_MONTHS.
  function lineChart(svgEl, points, series, yAxisUnit, xOpts) {
    xOpts = xOpts || {};
    var xKey = xOpts.key || "qlc_ratio";
    var xMin = xOpts.min !== undefined ? xOpts.min : 0;
    var xMax = xOpts.max !== undefined ? xOpts.max : 100;
    var xTicks = xOpts.ticks || [0, 25, 50, 75, 100];
    var xTickFormat = xOpts.tickFormat || function (t) { return t + "%"; };

    var W = 640, H = 220, padL = 58, padR = 12, padT = 12, padB = 24;
    var ys = [];
    series.forEach(function (s) {
      points.forEach(function (p) { ys.push(p[s.key]); });
    });
    var yMin = Math.min.apply(null, ys), yMax = Math.max.apply(null, ys);
    if (yMin === yMax) { yMin -= 1; yMax += 1; }
    var pad = (yMax - yMin) * 0.08;
    yMin -= pad; yMax += pad;
    function xPix(x) { return padL + ((x - xMin) / (xMax - xMin)) * (W - padL - padR); }
    function yPix(y) { return H - padB - ((y - yMin) / (yMax - yMin)) * (H - padT - padB); }

    var svg = "";
    var yTickCount = 4;
    for (var ti = 0; ti <= yTickCount; ti++) {
      var tv = yMin + (yMax - yMin) * (ti / yTickCount);
      var ty = yPix(tv);
      svg += '<line x1="' + padL + '" y1="' + ty.toFixed(1) + '" x2="' + (W - padR) + '" y2="' + ty.toFixed(1) +
        '" stroke="var(--border)" stroke-width="1" opacity="0.35" />';
      svg += '<text class="axis-label" x="' + (padL - 8) + '" y="' + (ty + 3).toFixed(1) +
        '" text-anchor="end">' + fmtAxisTick(tv) + '</text>';
    }
    series.forEach(function (s) {
      var path = points.map(function (p, i) {
        return (i === 0 ? "M" : "L") + xPix(p[xKey]).toFixed(1) + "," + yPix(p[s.key]).toFixed(1);
      }).join(" ");
      svg += '<path d="' + path + '" fill="none" stroke="' + s.color + '" stroke-width="2.5" />';
    });
    svg += '<line x1="' + padL + '" y1="' + padT + '" x2="' + padL + '" y2="' + (H - padB) +
      '" stroke="var(--border)" />';
    svg += '<line x1="' + padL + '" y1="' + (H - padB) + '" x2="' + (W - padR) + '" y2="' + (H - padB) +
      '" stroke="var(--border)" />';
    xTicks.forEach(function (t) {
      svg += '<text class="axis-label" x="' + xPix(t) + '" y="' + (H - padB + 14) + '" text-anchor="middle">' + xTickFormat(t) + '</text>';
    });
    if (yAxisUnit) {
      var midY = (padT + (H - padB)) / 2;
      svg += '<text class="axis-label axis-unit-label" x="14" y="' + midY.toFixed(1) +
        '" text-anchor="middle" transform="rotate(-90 14 ' + midY.toFixed(1) + ')">' +
        escapeXml(yAxisUnit) + '</text>';
    }
    svgEl.innerHTML = svg;
    return { xPix: xPix, yPix: yPix, padT: padT, H: H, padB: padB };
  }

  // Builds the two-series point array for a yield-ramp reference chart --
  // fixed x=month domain 0..RAMP_CHART_MONTHS, independent of the ratio
  // slider. Mirrors calc.yield_ramp_curve.
  function combinedRampPoints(matureA, coefA, matureB, coefB, months) {
    var pts = [];
    for (var t = 0; t <= months; t++) {
      pts.push({
        month: t,
        dedicated_yield_pct: yieldRampFraction(matureA, coefA, t) * 100,
        combo_yield_pct: yieldRampFraction(matureB, coefB, t) * 100,
      });
    }
    return pts;
  }

  function updateUnitLabels() {
    var bitUnit = bitUnitInput.value.trim() || "bit unit";
    var currencyUnit = currencyUnitInput.value.trim() || "cost unit";
    document.querySelectorAll(".unit-bit").forEach(function (el) { el.textContent = bitUnit; });
    document.querySelectorAll(".unit-currency").forEach(function (el) { el.textContent = currencyUnit; });
    // chartCostTitle is fixed to cent/GB (see costPerGbEokwonToCent) and no
    // longer depends on currencyUnit -- only the results table's Cost rows
    // (".unit-currency" above) still use currency_unit.
  }

  function readExchangeRate() {
    var raw = exchangeRateInput.value.trim();
    var num = Number(raw);
    var valid = raw !== "" && isFinite(num) && num > 0;
    exchangeRateInput.classList.toggle("invalid", raw !== "" && !valid);
    return valid ? num : 1300;
  }

  function isDirectCostMode() {
    return costModeDirectRadio.checked;
  }

  // Disables/greys the capex + dev-cost fields (COST_MODEL_ONLY_KEYS) when
  // "GB당 원가 직접 입력" is selected -- those fields are not used and are
  // skipped by required-field validation entirely in that mode. Bit
  // production fields (density/gross_die/yield/max_capa) are never disabled.
  function updateCostModeUI() {
    var direct = isDirectCostMode();
    COST_MODEL_ONLY_KEYS.forEach(function (key) {
      var el = paramInputs[key];
      el.disabled = direct;
      if (direct) el.classList.remove("invalid");
    });
    directCostFieldsEl.style.display = direct ? "grid" : "none";
    if (!direct) {
      comboDirectCostInput.classList.remove("invalid");
      dedicatedDirectCostInput.classList.remove("invalid");
    }
  }

  // Bit charts (1, 3) are fixed at 억GB (10^8 GB); cost charts (2, 4) are
  // fixed at cent/GB -- in cost_mode "model", converted from the
  // already-억원-denominated cost_per_gb via the current
  // exchange_rate_krw_per_usd input (see costPerGbEokwonToCent); in
  // cost_mode "direct", the two direct cent/GB inputs are used AS-IS, flat
  // across every ratio (no eokwon conversion, no ratio dependency). Never
  // used for the crossover comparison (that stays in raw Gb/currency_unit
  // terms in model mode).
  function chartPointsFromSweep(rows, exchangeRate, costMode, directCostCent) {
    return rows.map(function (r) {
      var comboCostCent, dedCostCent, fiveYearComboCostCent, fiveYearDedCostCent;
      if (costMode === "direct") {
        comboCostCent = directCostCent.combo;
        dedCostCent = directCostCent.dedicated;
        fiveYearComboCostCent = directCostCent.combo;
        fiveYearDedCostCent = directCostCent.dedicated;
      } else {
        comboCostCent = costPerGbEokwonToCent(r.combo_cost_per_gb, exchangeRate);
        dedCostCent = costPerGbEokwonToCent(r.dedicated_cost_per_gb, exchangeRate);
        fiveYearComboCostCent = costPerGbEokwonToCent(r.five_year_combo_cost_per_gb, exchangeRate);
        fiveYearDedCostCent = costPerGbEokwonToCent(r.five_year_dedicated_cost_per_gb, exchangeRate);
      }
      return {
        qlc_ratio: r.qlc_ratio,
        combo_bit_100m_gb: r.combo_bit_total_gb / 1e8,
        dedicated_bit_100m_gb: r.dedicated_bit_total_gb / 1e8,
        combo_cost_per_gb_cent: comboCostCent,
        dedicated_cost_per_gb_cent: dedCostCent,
        five_year_combo_bit_100m_gb: r.five_year_combo_bit_total_gb / 1e8,
        five_year_dedicated_bit_100m_gb: r.five_year_dedicated_bit_total_gb / 1e8,
        five_year_combo_cost_per_gb_cent: fiveYearComboCostCent,
        five_year_dedicated_cost_per_gb_cent: fiveYearDedCostCent,
      };
    });
  }

  function clearResults() {
    ["waferQlcCombo", "waferTlcCombo", "comboBit", "comboCost", "comboCostPerBit",
      "waferQlcDed", "waferTlcDed", "dedBit", "dedCost", "dedCostPerBit",
      "comboOneYearBit", "comboFiveYearBit", "dedOneYearBit", "dedFiveYearBit"].forEach(function (id) {
      document.getElementById(id).textContent = "—";
    });
    document.getElementById("qlcPct").textContent = "";
    document.getElementById("tlcPct").textContent = "";
    document.getElementById("verdict").textContent = "";
    document.getElementById("devCostNote").textContent = "";
    document.getElementById("erInfoNote").textContent = "";
    document.getElementById("fullBuildoutNote").textContent = "";
    document.getElementById("introStats").textContent = "";
    basisYieldNoteEl.textContent = "";
    basisMonthReadoutEl.textContent = "";
    ["chartBit", "chartCost", "chartFiveYearBit", "chartFiveYearCost",
      "chartYieldRampQlc", "chartYieldRampTlc"].forEach(function (id) {
      document.getElementById(id).innerHTML = "";
    });
    chartPlaceholder.style.display = "block";
    slider.disabled = true;
  }

  function render() {
    var ratio = Number(slider.value);
    var idx = nearestRowIndex(sweep, ratio);
    var row = sweep[idx];

    // "기준 시점" (yield basis) toggle -- ONLY feeds displaySweep below,
    // which in turn ONLY feeds charts 1-2 and the table's Bit 생산량/Cost per
    // bit cells. Every other read of `row` on this page (wafer/월, 1-year/
    // 5-year cumulative, verdict, dev-cost/ER/full-buildout notes, charts
    // 3-6) stays on the base `sweep`, i.e. always mature-yield, unaffected
    // by this toggle.
    var basisMode = currentYieldBasisMode();
    var basisMonths = currentYieldBasisMonths();
    basisMonthReadoutEl.textContent = basisMonths + "개월차";
    var displaySweep = computeDisplaySweep(currentParams, sweep, basisMode, basisMonths);
    var displayRow = displaySweep[idx];
    if (basisMode === "month") {
      var pctComboQlc = rampProgressPct(currentParams.combo_qlc_yield_ramp_coef, basisMonths);
      var pctComboTlc = rampProgressPct(currentParams.combo_tlc_yield_ramp_coef, basisMonths);
      var pctDedQlc = rampProgressPct(currentParams.qlc_yield_ramp_coef, basisMonths);
      var pctDedTlc = rampProgressPct(currentParams.tlc_yield_ramp_coef, basisMonths);
      basisYieldNoteEl.textContent =
        "특정 개월 기준: 생산 시작 후 " + basisMonths + "개월차의 실제 수율을 사용 — 성숙 수율 대비 도달 비율" +
        "(각 라인/레시피 자기 자신의 yield_ramp_coef 기준, mature_yield 값과 무관): 분리 QLC " + fmt(pctDedQlc) +
        "% / 분리 TLC " + fmt(pctDedTlc) + "% / 콤보 QLC " + fmt(pctComboQlc) + "% / 콤보 TLC " + fmt(pctComboTlc) + "%.";
    } else {
      basisYieldNoteEl.textContent =
        "성숙 수율(mature yield) 기준 — 아래 두 그래프와 표의 Bit 생산량/Cost per bit는 완전히 램프업된 이후의 값입니다.";
    }
    var basisLabel = basisMode === "month" ? (basisMonths + "개월차 기준") : "성숙 수율 기준";
    chartBitTitleEl.textContent = "Bit 생산량 vs QLC 비율 (억GB, " + basisLabel + ")";
    chartCostTitleEl.textContent = "Cost / GB vs QLC 비율 (cent/GB, 낮을수록 유리, " + basisLabel + ")";

    document.getElementById("qlcPct").textContent = "QLC " + row.qlc_ratio + "%";
    document.getElementById("tlcPct").textContent = "TLC " + row.tlc_ratio + "%";
    document.getElementById("waferQlcCombo").textContent = fmt(row.wafer_qlc_combo);
    document.getElementById("waferTlcCombo").textContent = fmt(row.wafer_tlc_combo);
    document.getElementById("waferQlcDed").textContent = fmt(row.wafer_qlc_dedicated);
    document.getElementById("waferTlcDed").textContent = fmt(row.wafer_tlc_dedicated);
    document.getElementById("comboBit").textContent = fmt(displayRow.combo_bit_total);
    document.getElementById("dedBit").textContent = fmt(displayRow.dedicated_bit_total);
    document.getElementById("comboOneYearBit").textContent =
      fmt(row.one_year_combo_bit_total_gb / 1e8) + " / " + fmt(row.one_year_combo_sale_bit_total_gb / 1e8);
    document.getElementById("comboFiveYearBit").textContent =
      fmt(row.five_year_combo_bit_total_gb / 1e8) + " / " + fmt(row.five_year_combo_sale_bit_total_gb / 1e8);
    document.getElementById("dedOneYearBit").textContent =
      fmt(row.one_year_dedicated_bit_total_gb / 1e8) + " / " + fmt(row.one_year_dedicated_sale_bit_total_gb / 1e8);
    document.getElementById("dedFiveYearBit").textContent =
      fmt(row.five_year_dedicated_bit_total_gb / 1e8) + " / " + fmt(row.five_year_dedicated_sale_bit_total_gb / 1e8);
    document.getElementById("introStats").textContent =
      "현재 비율(QLC " + row.qlc_ratio + "% / TLC " + row.tlc_ratio + "%) 기준 총 bit 생산량 — " +
      "콤보 생산 1년간 " + fmt(row.one_year_combo_bit_total_gb / 1e8) + " 억GB / 5년간 " +
      fmt(row.five_year_combo_bit_total_gb / 1e8) + " 억GB, 분리 생산 1년간 " +
      fmt(row.one_year_dedicated_bit_total_gb / 1e8) + " 억GB / 5년간 " +
      fmt(row.five_year_dedicated_bit_total_gb / 1e8) + " 억GB.";
    updateUnitLabels();

    var currencyUnit = currencyUnitInput.value.trim() || "cost unit";
    var direct = currentCostMode === "direct";

    if (direct) {
      document.getElementById("comboCost").textContent = "—";
      document.getElementById("dedCost").textContent = "—";
      document.getElementById("comboCostPerBit").textContent = "—";
      document.getElementById("dedCostPerBit").textContent = "—";
    } else {
      // Total cost is yield-independent (cost never depends on bit
      // production), so it's read from the base `row` regardless of basis --
      // only Cost/bit (denominator = bit_total) moves with the toggle.
      document.getElementById("comboCost").textContent = fmt(row.combo_cost_total);
      document.getElementById("dedCost").textContent = fmt(row.dedicated_cost_total);
      document.getElementById("comboCostPerBit").textContent = fmt(displayRow.combo_cost_per_bit);
      document.getElementById("dedCostPerBit").textContent = fmt(displayRow.dedicated_cost_per_bit);
    }

    var verdict = document.getElementById("verdict");
    var better = direct
      ? currentDirectCosts.combo <= currentDirectCosts.dedicated
      : row.combo_cost_per_bit <= row.dedicated_cost_per_bit;
    verdict.textContent = better
      ? "✓ 현재 비율(QLC " + row.qlc_ratio + "% / TLC " + row.tlc_ratio + "%)에서는 콤보 라인이 분리 생산보다 bit당 비용이 낮습니다."
      : "⚠ 현재 비율(QLC " + row.qlc_ratio + "% / TLC " + row.tlc_ratio + "%)에서는 분리 생산이 bit당 비용이 더 낮습니다.";

    var devCostNoteEl = document.getElementById("devCostNote");
    if (direct) {
      devCostNoteEl.textContent =
        "GB당 원가 직접 입력 모드: 투자비/개발비 입력은 계산에 반영되지 않습니다. Cost/GB (직접입력) — 콤보 " +
        fmt(currentDirectCosts.combo) + " cent/GB / 분리 " + fmt(currentDirectCosts.dedicated) + " cent/GB.";
    } else {
      devCostNoteEl.textContent =
        "1회성 개발비(인력+Mask 환산만, 모든 비율에 동일하게 반영됨 — ER wafer 비용은 wafer 처리 비용에 이미 포함되어 별도 계상하지 않음): 콤보 " +
        fmt(comboDev) + " " + currencyUnit + " / 분리 생산 " + fmt(dedDev) + " " + currencyUnit;
    }

    var erInfoNoteEl = document.getElementById("erInfoNote");
    var t95ComboQlc = yieldRampT95(currentParams.combo_qlc_yield_ramp_coef);
    var t95ComboTlc = yieldRampT95(currentParams.combo_tlc_yield_ramp_coef);
    var t95DedQlc = yieldRampT95(currentParams.qlc_yield_ramp_coef);
    var t95DedTlc = yieldRampT95(currentParams.tlc_yield_ramp_coef);
    erInfoNoteEl.textContent =
      "ER(엔지니어링 런) 기간 — 각 라인/레시피가 자기 성숙수율의 95%에 도달하는 시점(t95)까지, " +
      "매달 min(월간 소모량, 그 달 wafer_total) 만큼이 판매용에서 ER로 전환됩니다: 콤보 QLC " +
      fmt(t95ComboQlc) + "개월 / TLC " + fmt(t95ComboTlc) + "개월 (월 " + fmt(currentParams.er_wafer_combo) +
      " wafer) · 분리 QLC " + fmt(t95DedQlc) + "개월 / TLC " + fmt(t95DedTlc) + "개월 (월 " +
      fmt(currentParams.er_wafer_dedicated) + " wafer).";

    var fullBuildoutNoteEl = document.getElementById("fullBuildoutNote");
    if (direct) {
      fullBuildoutNoteEl.textContent =
        "전체 투자비용 (Max capa 풀 빌드아웃 기준): GB당 원가 직접 입력 모드에서는 투자비 모델을 사용하지 않으므로 해당 없음.";
    } else {
      fullBuildoutNoteEl.textContent =
        "전체 투자비용 (Max capa 풀 빌드아웃 기준): 콤보 " + fmt(buildout.combo) + " " + currencyUnit +
        " / 분리 " + fmt(buildout.dedicated) + " " + currencyUnit +
        " (콤보는 combo_qlc_max_capa를 대표 capa로 사용 — 근거는 report.md/README 참고, 실제 가동 비율과 무관한 고정값)";
    }

    chartPlaceholder.style.display = "none";
    var exchangeRate = readExchangeRate();
    // Charts 1-2 read the basis-toggle-aware displaySweep; charts 3-4 (5-year
    // cumulative) always read the base sweep (mature-yield), unaffected by
    // the toggle.
    var monthlyChartPoints = displayChartPointsFromSweep(displaySweep, exchangeRate, currentCostMode, currentDirectCosts);
    var fiveYearChartPoints = chartPointsFromSweep(sweep, exchangeRate, currentCostMode, currentDirectCosts);
    var charts = [
      { id: "chartBit", series: ["combo_bit_100m_gb", "dedicated_bit_100m_gb"], unit: "억GB", points: monthlyChartPoints },
      { id: "chartCost", series: ["combo_cost_per_gb_cent", "dedicated_cost_per_gb_cent"], unit: "cent/GB", points: monthlyChartPoints },
      { id: "chartFiveYearBit", series: ["five_year_combo_bit_100m_gb", "five_year_dedicated_bit_100m_gb"], unit: "억GB", points: fiveYearChartPoints },
      { id: "chartFiveYearCost", series: ["five_year_combo_cost_per_gb_cent", "five_year_dedicated_cost_per_gb_cent"], unit: "cent/GB", points: fiveYearChartPoints },
    ];
    var chartsInfo = charts.map(function (c) {
      return lineChart(document.getElementById(c.id), c.points,
        [{ key: c.series[0], color: "var(--combo)" }, { key: c.series[1], color: "var(--dedicated)" }],
        c.unit);
    });
    chartsInfo.forEach(function (info, idx) {
      var svgEl = document.getElementById(charts[idx].id);
      var x = info.xPix(row.qlc_ratio);
      svgEl.innerHTML += '<line x1="' + x + '" y1="' + info.padT + '" x2="' + x + '" y2="' + (info.H - info.padB) +
        '" stroke="var(--fg)" stroke-width="1" stroke-dasharray="2,3" opacity="0.5" />';
    });

    // Yield-ramp reference charts -- fixed x=month domain, independent of
    // the ratio slider (no dashed ratio-indicator line drawn on these two).
    var rampXOpts = {
      key: "month", min: 0, max: RAMP_CHART_MONTHS,
      ticks: [0, 6, 12, 18, 24, 30, 36], tickFormat: function (t) { return t; },
    };
    var qlcRampPoints = combinedRampPoints(
      currentParams.qlc_mature_yield, currentParams.qlc_yield_ramp_coef,
      currentParams.combo_qlc_mature_yield, currentParams.combo_qlc_yield_ramp_coef,
      RAMP_CHART_MONTHS
    );
    var tlcRampPoints = combinedRampPoints(
      currentParams.tlc_mature_yield, currentParams.tlc_yield_ramp_coef,
      currentParams.combo_tlc_mature_yield, currentParams.combo_tlc_yield_ramp_coef,
      RAMP_CHART_MONTHS
    );
    lineChart(document.getElementById("chartYieldRampQlc"), qlcRampPoints,
      [{ key: "dedicated_yield_pct", color: "var(--dedicated)" }, { key: "combo_yield_pct", color: "var(--combo)" }],
      "%", rampXOpts);
    lineChart(document.getElementById("chartYieldRampTlc"), tlcRampPoints,
      [{ key: "dedicated_yield_pct", color: "var(--dedicated)" }, { key: "combo_yield_pct", color: "var(--combo)" }],
      "%", rampXOpts);
  }

  function readRequiredParams() {
    var values = {}, missing = [];
    var direct = isDirectCostMode();
    REQUIRED_KEYS.forEach(function (key) {
      var el = paramInputs[key];
      if (direct && COST_MODEL_ONLY_KEYS.indexOf(key) !== -1) {
        el.classList.remove("invalid");
        values[key] = 0;
        return;
      }
      var raw = el.value.trim();
      var num = Number(raw);
      var valid = raw !== "" && isFinite(num);
      el.classList.toggle("invalid", !valid);
      if (valid) { values[key] = num; } else { missing.push(PARAM_LABELS[key] + " (" + key + ")"); }
    });
    return { values: values, missing: missing };
  }

  function readDirectCostInputs() {
    var direct = isDirectCostMode();
    var result = { combo: 0, dedicated: 0, missing: [] };
    if (!direct) {
      comboDirectCostInput.classList.remove("invalid");
      dedicatedDirectCostInput.classList.remove("invalid");
      return result;
    }
    [
      ["combo", comboDirectCostInput, "콤보 GB당 원가 (combo_direct_cost_per_gb)"],
      ["dedicated", dedicatedDirectCostInput, "분리 GB당 원가 (dedicated_direct_cost_per_gb)"],
    ].forEach(function (t) {
      var raw = t[1].value.trim();
      var num = Number(raw);
      var valid = raw !== "" && isFinite(num) && num >= 0;
      t[1].classList.toggle("invalid", !valid);
      if (valid) { result[t[0]] = num; } else { result.missing.push(t[2]); }
    });
    return result;
  }

  function readRatioStep() {
    var raw = ratioStepInput.value.trim();
    var num = parseInt(raw, 10);
    var valid = raw !== "" && isFinite(num) && num > 0 && num <= 100;
    ratioStepInput.classList.toggle("invalid", raw !== "" && !valid);
    return valid ? num : 5;
  }

  function recomputeAndRender() {
    updateCostModeUI();
    var parsed = readRequiredParams();
    var directCosts = readDirectCostInputs();
    var missing = parsed.missing.concat(directCosts.missing);
    if (missing.length > 0) {
      errorBanner.style.display = "block";
      errorBanner.textContent = "다음 파라미터를 입력하거나 값을 확인해 주세요: " + missing.join(", ");
      clearResults();
      return;
    }
    errorBanner.style.display = "none";
    slider.disabled = false;

    var ratioStep = readRatioStep();
    slider.step = ratioStep;
    var snapped = Math.round(Number(slider.value) / ratioStep) * ratioStep;
    slider.value = Math.max(0, Math.min(100, snapped));

    currentParams = parsed.values;
    currentCostMode = isDirectCostMode() ? "direct" : "model";
    currentDirectCosts = directCosts;
    var result = computeSweep(parsed.values, ratioStep);
    sweep = result.rows;
    comboDev = result.comboDev;
    dedDev = result.dedDev;
    buildout = fullBuildout(parsed.values);
    render();
  }

  slider.addEventListener("input", render);
  // "기준 시점" toggle is a pure display lens over the already-computed base
  // sweep -- no param recompute needed, just a re-render.
  yieldBasisMatureRadio.addEventListener("change", function () {
    updateBasisModeUI();
    if (sweep.length > 0) render();
  });
  yieldBasisMonthRadio.addEventListener("change", function () {
    updateBasisModeUI();
    if (sweep.length > 0) render();
  });
  basisMonthSlider.addEventListener("input", function () {
    if (sweep.length > 0) render();
  });
  REQUIRED_KEYS.forEach(function (key) {
    paramInputs[key].addEventListener("input", recomputeAndRender);
  });
  bitUnitInput.addEventListener("input", updateUnitLabels);
  currencyUnitInput.addEventListener("input", function () {
    // currency_unit no longer affects charts 1-4 (fixed cent/GB), but the
    // full-buildout TEXT line draws its number directly in currency_unit
    // (no cent conversion) -- redraw so that text stays in sync without a
    // full param recompute.
    updateUnitLabels();
    if (sweep.length > 0) render();
  });
  exchangeRateInput.addEventListener("input", function () {
    // exchange_rate_krw_per_usd feeds the Cost chart's cent/GB axis directly
    // (model mode only) -- redraw so the axis stays in sync without a full
    // param recompute.
    if (sweep.length > 0) render();
  });
  ratioStepInput.addEventListener("input", recomputeAndRender);
  costModeModelRadio.addEventListener("change", recomputeAndRender);
  costModeDirectRadio.addEventListener("change", recomputeAndRender);
  comboDirectCostInput.addEventListener("input", recomputeAndRender);
  dedicatedDirectCostInput.addEventListener("input", recomputeAndRender);
  document.getElementById("resetAll").addEventListener("click", function () {
    resetAllInputs();
    recomputeAndRender();
  });
  document.getElementById("clearAll").addEventListener("click", function () {
    clearAllInputs();
    recomputeAndRender();
  });

  updateBasisModeUI();
  resetAllInputs();
  recomputeAndRender();
})();
</script>
</body>
</html>
"""


def _param_fields_html() -> str:
    parts: list[str] = []
    for gid, glabel, fields in PARAM_GROUPS:
        parts.append(f'<fieldset class="field-group" id="group-{gid}">')
        parts.append(f"<legend>{glabel}</legend>")
        parts.append('<div class="field-grid">')
        for key, label in fields:
            parts.append(
                '<div class="field">'
                f'<label for="param_{key}">{label} <code>{key}</code></label>'
                f'<input id="param_{key}" type="number" step="any" inputmode="decimal">'
                "</div>"
            )
        parts.append("</div>")
        parts.append("</fieldset>")
    return "\n".join(parts)


def blank_payload() -> dict:
    """Payload for a params-file-less scaffold: every required fab parameter
    is blank (so the browser calculator opens empty and prompts the user to
    fill it in), display settings default to calc.py's neutral values. No
    sweep/crossover/dev-cost numbers are fabricated."""
    params: dict[str, object] = {k: "" for k in calc.REQUIRED_KEYS}
    params.update(calc.OPTIONAL_STR_DEFAULTS)
    return {
        "params": params,
        "sweep": [],
        "crossover": {"exists": False},
        "dev_cost": {"combo": 0, "dedicated": 0},
        "full_buildout": {"combo": 0, "dedicated": 0},
        "yield_ramp_curves": {},
        "t95_months": {},
        "er_wafer_rate_assumption": calc.ER_WAFER_RATE_ASSUMPTION,
        "cost_mode": calc.OPTIONAL_STR_DEFAULTS["cost_mode"],
        "direct_cost_per_gb": {"combo": 0, "dedicated": 0},
        "best_combo_bit_production": None,
        "best_combo_cost_per_bit": None,
        "best_dedicated_bit_production": None,
        "best_dedicated_cost_per_bit": None,
        "currency_unit": calc.OPTIONAL_STR_DEFAULTS["currency_unit"],
        "bit_unit": calc.OPTIONAL_STR_DEFAULTS["bit_unit"],
        "is_sample": False,
    }


def _build_html(payload: dict) -> str:
    sweep_rows = payload.get("sweep") or []
    step = sweep_rows[1]["qlc_ratio"] - sweep_rows[0]["qlc_ratio"] if len(sweep_rows) > 1 else 5
    default_ratio = min(sweep_rows, key=lambda r: abs(r["qlc_ratio"] - 50))["qlc_ratio"] if sweep_rows else 50
    banner = SAMPLE_BANNER_HTML if payload.get("is_sample") else ""

    return (
        TEMPLATE
        .replace("__STEP__", str(int(step)))
        .replace("__DEFAULT__", str(int(default_ratio)))
        .replace("__SAMPLE_BANNER__", banner)
        .replace("__PARAM_FIELDS__", _param_fields_html())
        .replace("__REQUIRED_KEYS_JSON__", json.dumps(calc.REQUIRED_KEYS, ensure_ascii=False))
        .replace("__PARAM_LABELS_JSON__", json.dumps(PARAM_LABELS, ensure_ascii=False))
        .replace("__COST_MODEL_ONLY_KEYS_JSON__", json.dumps(calc.COST_MODEL_ONLY_KEYS, ensure_ascii=False))
        .replace("__RAMP_CHART_MONTHS_JSON__", json.dumps(calc.RAMP_CHART_MONTHS))
        .replace("__PAYLOAD_JS__", _payload_js_literal(payload))
    )


def render(sweep_json_path: Path, html_path: Path) -> None:
    payload = json.loads(sweep_json_path.read_text(encoding="utf-8"))
    html = _build_html(payload)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")


def render_blank(html_path: Path) -> None:
    html = _build_html(blank_payload())
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) == 2 and argv[0] == "--blank":
        render_blank(Path(argv[1]))
        print(f"wrote {argv[1]}")
        return 0
    if len(argv) != 2:
        print("usage: render_html.py <sweep.json> <output_html_path>", file=sys.stderr)
        print("   or: render_html.py --blank <output_html_path>", file=sys.stderr)
        return 1
    render(Path(argv[0]), Path(argv[1]))
    print(f"wrote {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
