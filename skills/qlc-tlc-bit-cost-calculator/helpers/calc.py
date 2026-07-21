#!/usr/bin/env python3
"""Deterministic QLC vs TLC bit-cost calculator.

Compares two fab strategies for meeting a QLC:TLC market demand mix, both
expressed as a full sweep over the same 0-100% QLC:TLC ratio `r`. Each line
carries its OWN 100%-utilization max wafer capacity — dedicated and combo
are separate investments/lines, so their max capacities are independent
numbers, not shares of one fab-wide pool.

Unit conventions (labels only — the calculation STRUCTURE below is
unchanged; these are conversion layers applied where each raw field is
consumed):
  - `*_mature_yield` fields are entered as a percentage (e.g. `82` means
    82%) and divided by 100 wherever they feed `bit_per_wafer` — this is the
    FULLY RAMPED (mature) yield a line/recipe converges toward, not its
    yield at any particular point in time (see "Yield ramp-up" below).
  - `*_capex_per_wafer` fields are entered as cost per 10,000 wafers (e.g.
    `6200` means 6200 currency-units to produce 10,000 wafers) and divided
    by 10,000 wherever they're used as a per-wafer rate.
  - `*_density` fields are labeled `Gb/Wafer`; `bit_per_wafer` is computed
    exactly as before (`density * grossdie_per_wafer * yield`) — density is
    NOT itself converted, only the resulting bit totals are, at the
    display/output layer (GB = raw bit total / 8, per `bit_total_gb` below).
  - `*_max_capa` fields are wafer/month counts, calculation unchanged.
  - `er_wafer_combo` / `er_wafer_dedicated` are each a MONTHLY ER-wafer
    consumption RATE (wafer/month), not a one-time total — see "ER wafers
    and the sale/ER wafer split" below.

Display-only cent/GB conversion (visualization.html's Cost chart y-axis
ONLY, see `cost_per_gb_eokwon_to_cent` below): `exchange_rate_krw_per_usd`
(원/달러, optional display setting alongside currency_unit/bit_unit/
ratio_step, default 1300) converts a cost/GB figure that is assumed already
denominated in 억원 into cent/GB, since 억원-scale numbers round to ~0 on a
linear axis and make the chart unreadable. Nothing else (sweep.csv,
report.md, the results table's Cost/Cost-per-bit rows) is affected — they
keep showing `{currency_unit}/GB` as before. `cost_mode == "direct"` is the
one exception (see "Cost calculation modes" below): its GB-cost inputs are
ALREADY denominated in cent/GB, so no eokwon conversion is applied to them.

  1. "dedicated"  — a QLC-only line AND a separate TLC-only line (own die
                     design each, own investment). `qlc_max_capa` is the
                     QLC-only line's max capacity at 100% utilization;
                     `tlc_max_capa` is the TLC-only line's own max capacity
                     at 100% utilization — the two can differ. At ratio `r`
                     the QLC line runs at r% of ITS OWN max
                     (`wafer_qlc_dedicated = qlc_max_capa * r/100`) and the
                     TLC line runs at (100-r)% of ITS OWN max
                     (`wafer_tlc_dedicated = tlc_max_capa * (100-r)/100`).
  2. "combo"      — a single flexible line built around the QLC die design
                     that can also run a TLC recipe. `combo_capex_per_wafer`
                     / `combo_gross_die` are shared by both recipes (same
                     physical line and die); only density and yield are
                     recipe-specific. The combo line is physically one line
                     that is always 100% utilized (time-sharing QLC/TLC
                     recipes, never idle), but its max capacity can differ
                     slightly by recipe (`combo_qlc_max_capa` vs
                     `combo_tlc_max_capa`), so at ratio `r` it runs
                     `wafer_qlc_combo = combo_qlc_max_capa * r/100` in
                     QLC-recipe mode and
                     `wafer_tlc_combo = combo_tlc_max_capa * (100-r)/100`
                     in TLC-recipe mode.

Because each line sweeps its OWN max capacity by the ratio (rather than all
four sharing one pool), dedicated and combo remain directly comparable at
every point of the sweep without assuming their total investment sizes are
equal.

Cost and bit production come straight from physical parameters — the only
tuning coefficients are the two flat dev-cost conversion rates below
(headcount and mask cost), both shared across scenarios:

  bit_per_wafer = density_per_die * grossdie_per_wafer * (mature_yield_pct / 100)
  cost(line)    = (capex_per_10k_wafer / 10000) * wafer_count

("Monthly" snapshot rows — the original two charts/table plus the
crossover — always assume a FULLY RAMPED line, i.e. `mature_yield_pct` used
directly, exactly as `*_yield` was used before this field was renamed. Only
the 1-year/5-year cumulative views below actually walk the ramp-up month by
month. This monthly snapshot, and the crossover derived from it, are
entirely UNCHANGED by everything below this point in the docstring.)

Yield ramp-up (Normalized Exponential Saturation): each of the four
lines/recipes (`qlc`, `tlc`, `combo_qlc`, `combo_tlc`) carries a pair of
fields instead of a single `*_yield` — `*_mature_yield` (the % yield once
fully ramped, same meaning/units as the old `*_yield`) and
`*_yield_ramp_coef` (1/month; larger = faster ramp-up to mature yield).
Elapsed months `t` are counted from that line/recipe's OWN production start
(t=0 at start of production, NOT calendar time):

  yield_fraction(t) = mature_yield_fraction * (1 - exp(-ramp_coef * t))

`yield_ramp_fraction()` / `yield_ramp_curve()` below implement this.

ER (engineering-run) period and t95 (NEW MODEL — replaces the old shared
`dev_ramp_months` assumption entirely; there is no longer any single shared
"months of zero production" parameter):

Each of the four lines/recipes independently reaches 95% of ITS OWN mature
yield at a month count `t95` that depends ONLY on that line's/recipe's own
`*_yield_ramp_coef` (not on `*_mature_yield` at all — the 95%-of-mature
point cancels the mature yield out of the equation):

  mature * (1 - exp(-k * t95)) = 0.95 * mature
  =>  t95 = ln(20) / k

`yield_ramp_t95()` implements this. `t=0..t95` (months since THAT line's/
recipe's own production start) is defined as that line's/recipe's own
"ER(엔지니어링 런)/qualification period" — every month within it, that
line/recipe consumes ER wafers.

ER wafers and the sale/ER wafer split (NEW MODEL): `er_wafer_combo` /
`er_wafer_dedicated` are each a MONTHLY ER-wafer consumption RATE (wafer/
month) for their scenario — NOT a one-time total wafer count like before.
Crucially, ER wafers are NOT produced on top of `wafer_total` (the line's
normal ratio-swept wafer volume, unchanged: `qlc_max_capa * r/100` etc.) —
`wafer_total` itself never changes. Instead, in every month that falls
inside a line's/recipe's own ER period (t <= its own t95), up to
`min(er_wafer_rate, wafer_total)` of that month's `wafer_total` wafers are
consumed as ER wafers, and the remainder is sold; outside the ER period,
100% of `wafer_total` is sold:

  sale_wafer(t) = wafer_total - (min(er_wafer_rate, wafer_total) if t <= t95 else 0)

`er_wafer_combo` is applied, independently and in full (not split 50/50),
to BOTH combo's QLC recipe and combo's TLC recipe — each recipe has its own
t95 (from its own ramp_coef) and its own `wafer_total`, but they draw on the
same monthly rate. `er_wafer_dedicated` is applied the same way to BOTH the
dedicated QLC line and the dedicated TLC line. See
`ER_WAFER_RATE_ASSUMPTION` below — this mirrors how `combo_headcount` /
`dedicated_headcount` are also single scenario-level values used as-is on
each of a scenario's two lines/recipes, not split between them.

The TOTAL bit production formula is completely UNCHANGED by any of this —
`wafer_total` never changes, so `total_bit(t) = wafer_total *
density*gross_die*yield_fraction(t)` already implicitly includes whatever
ER wafers were processed that month (ER wafers are good die too, just not
sold). What's NEW is a separate SALE-only bit figure:

  sale_bit(t) = sale_wafer(t) * density * gross_die * yield_fraction(t)

Both `total_bit` and `sale_bit` are summed month-by-month over each
cumulative window (see below) — `cumulative_ramp_bit_per_wafer()` (total,
unchanged) and the sale-bit split computed via `line_ramp_stats()` (new) in
`sweep()`.

One-time development cost (NEW MODEL — ER wafers no longer contribute a
one-time cost component; see "ER wafers" above for why): each scenario's
one-time dev cost now has only TWO components, both added once (flat, not
ratio-scaled):
  1. Headcount required to develop the product (`combo_headcount` /
     `dedicated_headcount`), converted via the shared coefficient
     `coef_cost_per_headcount`.
  2. Mask sets consumed (`combo_mask_count` / `dedicated_mask_count`),
     converted via the shared coefficient `coef_cost_per_mask`.

  dev_cost(combo)      = combo_headcount * coef_cost_per_headcount
                        + combo_mask_count * coef_cost_per_mask
  dev_cost(dedicated)  = dedicated_headcount * coef_cost_per_headcount
                        + dedicated_mask_count * coef_cost_per_mask

The old "ER wafer count * capex_per_wafer" one-time cost term (and the
`DEDICATED_ER_ASSUMPTION` 50/50 capex-blend it required) has been REMOVED
outright, not just zeroed — `wafer_total * capex_rate_per_wafer` (the
regular per-wafer cost, unchanged) already pays for every wafer processed,
ER or not, so a separate ER-wafer cost line was double-counting. There is
no dedicated-ER-cost assumption left to state.

Cost calculation modes (`cost_mode`, optional, default `"model"`): this
calculator can compute GB-cost two different ways. The physical bit
production model (density/gross_die/yield-ramp/max_capa/ER split) is
ALWAYS used for bit production, regardless of this setting — `cost_mode`
affects ONLY cost. `er_wafer_combo` / `er_wafer_dedicated` therefore stay
ACTIVE (never disabled/skipped by validation) in BOTH cost modes, unlike
the capex/dev-cost fields in `COST_MODEL_ONLY_KEYS` below — ER wafers now
feed the bit-production split (sale vs total), which is cost-mode-agnostic.

  - `"model"`  (default): cost/GB comes from the capex + dev-cost model
    described above (unchanged behavior).
  - `"direct"`: ignore the entire capex/dev-cost model. The two optional
    fields `combo_direct_cost_per_gb` / `dedicated_direct_cost_per_gb`
    (entered directly in **cent/GB**, ratio-independent flat numbers) are
    used as-is for the Cost/GB charts instead of the swept, model-derived
    cost/GB. `sweep.csv`/`sweep.json` still carry the full model-based cost
    fields for every row (nothing is deleted from the row schema), but the
    payload's top-level `direct_cost_per_gb` + `cost_mode` fields tell the
    display layer (`report.md`, `visualization.html`) which numbers are the
    ones that actually apply — capex/dev-cost total-cost/cost-per-bit/
    full-buildout figures are model concepts that don't have a coherent
    meaning once the model is bypassed, so they are reported as
    not-applicable in this mode rather than silently shown alongside a
    disconnected direct GB-cost.

Reads a `key=value` params file (see automations/qlc-tlc-bit-cost-calculator/
samples/sample-1.txt for the field list) and writes:

  - sweep.csv   — combo AND dedicated scenarios swept over the same mix ratio
  - sweep.json  — same data + raw params + crossover (for the HTML viz's
                  live recompute)
  - summary.json — headline numbers used to render summary.md

1-year (12-month) and 5-year (60-month) cumulative views (display-derived
from the same per-ratio sweep; NO development/qualification months are
skipped anymore — production starts at month 1 and every one of the 12 or
60 months is summed, each using that month's own ramped yield):

Cost does NOT depend on yield (cost is paid per wafer processed, not per
good bit), so the cumulative cost total is a flat monthly wafer-cost rate
times the FULL window length, plus the one-time dev cost added once:

  N_year_cost_total = monthly_wafer_cost * N_MONTHS + dev_cost   # one-time, added once

Bit production DOES depend on yield, and yield ramps up over time (see
"Yield ramp-up" above), so the cumulative bit total is an actual
month-by-month sum, walking each of the four lines'/recipes' OWN ramp curve
from its OWN t=0 (production month 1 through N_MONTHS):

  N_year_bit_total(line) = wafer_count(line) * sum_{t=1}^{N_MONTHS}
                            density(line) * gross_die(line) * yield_fraction(t; line)

`cumulative_ramp_bit_per_wafer()` implements this per-line sum (unchanged
from before); `line_ramp_stats()` (new) additionally precomputes the same
sum restricted to just that line's/recipe's own ER period
(t=1..min(t95, N_MONTHS)), which is exactly what's needed to split the
total into `N_year_bit_total` (unchanged formula/value) and a NEW
`N_year_sale_bit_total` (total minus whatever bit the ER-consumed wafers
would have produced) without a second month-by-month loop per ratio row —
see `sweep()`.

`monthly_wafer_cost` is each row's total cost MINUS its one-time dev_cost
(dev_cost is already folded into `combo_cost_total`/`dedicated_cost_total`
— see `sweep()` below).

Full max-capa buildout (ratio-independent, two scalars not a sweep): what
each scenario would cost if it built every one of its lines out to their own
100%-utilization max capacity, regardless of the demand ratio actually
served. Dedicated has two independent lines, so both are summed. This
number is a MODEL concept (capex-based) — it is still computed whenever
capex/dev-cost fields are present, but is only meaningful when
`cost_mode == "model"`; the display layer states it as one line of text
(not a chart) in the results panel, not a graph:

  full_buildout(dedicated) = qlc_capex_rate * qlc_max_capa
                           + tlc_capex_rate * tlc_max_capa
                           + dedicated_dev_cost

Combo is physically ONE line, so it has only one buildout size — but it
carries two max-capa fields (`combo_qlc_max_capa` / `combo_tlc_max_capa`)
because the same physical line yields slightly different throughput ceilings
depending which recipe runs. This calculator uses `combo_qlc_max_capa` as the
representative buildout capacity (see `COMBO_FULL_CAPEX_ASSUMPTION` below for
the rationale — restated in report.md/README so it's never a silently
invented number):

  full_buildout(combo) = combo_capex_rate * combo_qlc_max_capa + combo_dev_cost

Usage:
    python3 calc.py <params_file> <outputs_dir> [--step N] [--sample]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

REQUIRED_KEYS = [
    # Dedicated QLC-only line (own investment, own 100%-utilization max capa)
    "qlc_capex_per_wafer", "qlc_density", "qlc_gross_die",
    "qlc_mature_yield", "qlc_yield_ramp_coef", "qlc_max_capa",
    # Dedicated TLC-only line (own investment, own 100%-utilization max capa)
    "tlc_capex_per_wafer", "tlc_density", "tlc_gross_die",
    "tlc_mature_yield", "tlc_yield_ramp_coef", "tlc_max_capa",
    # Combo line — shared across both recipes (one physical line/die design)
    "combo_capex_per_wafer", "combo_gross_die",
    # Combo line — recipe-specific (density/yield AND each recipe's own max capa)
    "combo_qlc_density", "combo_qlc_mature_yield", "combo_qlc_yield_ramp_coef", "combo_qlc_max_capa",
    "combo_tlc_density", "combo_tlc_mature_yield", "combo_tlc_yield_ramp_coef", "combo_tlc_max_capa",
    # Monthly ER-wafer consumption RATE (wafer/month, NOT a one-time total) —
    # applied independently to both lines/recipes of its scenario during
    # each one's own ER period (t <= that line's/recipe's own t95). Feeds the
    # bit-production sale/ER split, so it stays active in BOTH cost modes.
    "er_wafer_combo", "er_wafer_dedicated",
    # One-time dev cost — headcount required, per scenario
    "combo_headcount", "dedicated_headcount",
    # One-time dev cost — mask sets consumed, per scenario
    "combo_mask_count", "dedicated_mask_count",
    # One-time dev cost — shared conversion coefficients (not split combo/dedicated)
    "coef_cost_per_headcount", "coef_cost_per_mask",
]

# The subset of REQUIRED_KEYS that feed ONLY the capex/dev-cost cost MODEL —
# never bit production. When cost_mode == "direct", visualization.html
# disables/greys these out and skips required-field validation on them (the
# model is bypassed entirely for cost), while calc.py's file-based path
# still requires them present (a params file is expected to carry the full
# field set even if a given run reports cost_mode == "direct"). NOTE:
# er_wafer_combo/er_wafer_dedicated are deliberately NOT in this list — they
# now feed the bit-production sale/ER split (see module docstring), which is
# needed regardless of cost_mode.
COST_MODEL_ONLY_KEYS = [
    "qlc_capex_per_wafer", "tlc_capex_per_wafer", "combo_capex_per_wafer",
    "combo_headcount", "dedicated_headcount",
    "combo_mask_count", "dedicated_mask_count",
    "coef_cost_per_headcount", "coef_cost_per_mask",
]

# 1 GB = 8 Gb. Raw bit totals below (combo_bit_total / dedicated_bit_total)
# come out of bit_per_wafer in Gb (density fields are labeled Gb/Wafer); this
# divisor is applied ONLY at the display/output layer (sweep row *_gb
# fields, charts, report.md) — the raw Gb math itself is untouched.
GB_PER_GIGABIT = 8.0

# capex_per_wafer fields are entered as cost per 10,000 wafers; this divisor
# converts to an effective per-wafer rate wherever capex feeds a cost
# calculation.
WAFER_BATCH_FOR_CAPEX = 10000.0

OPTIONAL_STR_DEFAULTS = {
    "currency_unit": "cost unit",
    "bit_unit": "bit unit",
    "ratio_step": "5",
    # 원/달러 환율 — ONLY consumed by visualization.html's Cost chart y-axis
    # (see cost_per_gb_eokwon_to_cent below); currency_unit/report.md/the
    # results table are entirely unaffected by this field.
    "exchange_rate_krw_per_usd": "1300",
    # Cost calculation mode toggle — "model" (default, capex/dev-cost model)
    # or "direct" (bypass the model entirely, use the two fields below).
    # Bit production is unaffected by this setting either way.
    "cost_mode": "model",
    # GB-cost direct inputs, entered ALREADY in cent/GB (not currency_unit) —
    # only consumed when cost_mode == "direct". Default 0 (unused) when mode
    # is "model".
    "combo_direct_cost_per_gb": "0",
    "dedicated_direct_cost_per_gb": "0",
}

# Cumulative windows used by the "1년 누적"/"5년 누적" charts and figures, in
# months. Production is assumed to start at month 1 of BOTH windows — there
# is no shared "development/ramp months" skip anymore (see module docstring;
# each line's/recipe's own ER period, t95, replaces that shared assumption).
ONE_YEAR_MONTHS = 12.0
FIVE_YEAR_MONTHS = 60.0

# Yield-ramp reference chart window (months since that line/recipe's own
# production start, t=0..RAMP_CHART_MONTHS inclusive) — a fixed reference
# curve purely for tuning mature_yield/ramp_coef by eye.
RAMP_CHART_MONTHS = 36

# The Cost chart's y-axis is fixed to cent/GB (currency_unit produces
# numbers too small to read once currency_unit is 억원-scale, e.g. combo
# cost/GB ~= 0.0003억원 -- the axis rounds to 0 and the chart looks empty).
# This conversion assumes cost_per_gb is ALREADY a plain numeric 억원 amount
# (the project's currency_unit convention), regardless of what currency_unit
# text the params file sets -- it is a display-layer conversion applied only
# to the Cost chart's axis, not to sweep.csv/report.md/the results table
# (those keep showing currency_unit/GB as before). NOTE: this conversion is
# skipped entirely when cost_mode == "direct", since those inputs are
# already denominated in cent/GB.
WON_PER_EOKWON = 100_000_000.0  # 1 억원 = 100,000,000 원
CENT_PER_USD = 100.0

# Modeling assumption for how the two monthly ER-wafer RATE parameters
# (er_wafer_combo / er_wafer_dedicated) are applied: each is a single
# scenario-level rate used independently (NOT split 50/50) on BOTH of that
# scenario's two lines/recipes -- combo's QLC recipe and TLC recipe each
# separately consume up to er_wafer_combo wafers/month during their OWN ER
# period; dedicated's QLC line and TLC line each separately consume up to
# er_wafer_dedicated wafers/month during their OWN ER period. This mirrors
# how combo_headcount/dedicated_headcount are also single scenario-level
# values used as-is, not split between the two lines/recipes.
ER_WAFER_RATE_ASSUMPTION = (
    "er_wafer_combo / er_wafer_dedicated are each a single monthly ER-wafer "
    "consumption RATE for their scenario, applied independently (in full, "
    "not split 50/50) to BOTH of that scenario's two lines/recipes -- "
    "combo's QLC recipe and TLC recipe each separately consume up to "
    "er_wafer_combo wafers/month during their OWN ER period (t <= that "
    "recipe's own t95); dedicated's QLC line and TLC line each separately "
    "consume up to er_wafer_dedicated wafers/month during their OWN ER "
    "period. This mirrors combo_headcount/dedicated_headcount, which are "
    "also single scenario-level values used as-is on both lines/recipes."
)

# Modeling assumption for the "전체 투자비용" full-buildout figure: combo is
# physically ONE line, so it needs exactly one buildout size, but it carries
# two max-capa fields (combo_qlc_max_capa / combo_tlc_max_capa) because the
# same physical line's throughput ceiling differs slightly by which recipe
# runs. combo_qlc_max_capa is chosen as the representative buildout capacity
# because the line is built around the QLC die design (combo_gross_die /
# combo_capex_per_wafer are already shared across both recipes in this
# model) -- the TLC-recipe max capa is treated as a derived operating mode of
# that same physical investment, not a separate size to build out to. This
# is a stated modeling choice, not a supplied number -- restate it wherever
# the full-buildout figures are reported (report.md / README). This figure
# is shown as TEXT in the results panel (not a chart) and is only meaningful
# when cost_mode == "model".
COMBO_FULL_CAPEX_ASSUMPTION = (
    "combo's full max-capa buildout uses combo_qlc_max_capa as the "
    "representative capacity (not combo_tlc_max_capa, and not the larger of "
    "the two): combo is one physical line built around the QLC die design "
    "(combo_capex_per_wafer/combo_gross_die are already shared across both "
    "recipes), so its buildout size is set by the QLC recipe's max "
    "throughput -- the TLC-recipe max capa is a derived operating mode of "
    "that same physical investment, not a separate buildout to size for."
)


class ParamsError(ValueError):
    pass


def parse_params(text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise ParamsError(f"line {lineno}: expected key=value, got: {raw!r}")
        key, value = line.split("=", 1)
        params[key.strip()] = value.strip()
    return params


def load_params(path: Path) -> dict[str, float | str]:
    raw = parse_params(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise ParamsError(f"missing required keys: {', '.join(missing)}")

    out: dict[str, float | str] = {}
    for k in REQUIRED_KEYS:
        try:
            out[k] = float(raw[k])
        except ValueError as e:
            raise ParamsError(f"key {k!r} must be numeric, got {raw[k]!r}") from e
    for k, default in OPTIONAL_STR_DEFAULTS.items():
        out[k] = raw.get(k, default)
    return out


def bit_per_wafer(density: float, gross_die: float, yield_: float) -> float:
    return density * gross_die * yield_


def yield_fraction(yield_pct: float) -> float:
    """`*_mature_yield` fields are entered as a percentage (82 means 82%)."""
    return yield_pct / 100.0


def yield_ramp_fraction(mature_yield_pct: float, ramp_coef: float, t: float) -> float:
    """Normalized Exponential Saturation: yield_fraction(t) = mature_yield_fraction
    * (1 - exp(-ramp_coef * t)), where t is months elapsed since THIS
    line/recipe's own production start (t=0 at start of production)."""
    return yield_fraction(mature_yield_pct) * (1.0 - math.exp(-ramp_coef * t))


def yield_ramp_curve(mature_yield_pct: float, ramp_coef: float, months: int = RAMP_CHART_MONTHS) -> list[dict]:
    """Fixed reference curve (t=0..months) for the yield-ramp charts —
    ratio-independent, purely for tuning mature_yield/ramp_coef by eye."""
    return [
        {"month": t, "yield_pct": yield_ramp_fraction(mature_yield_pct, ramp_coef, t) * 100.0}
        for t in range(0, months + 1)
    ]


def yield_ramp_progress_pct(ramp_coef: float, t: float) -> float:
    """Percentage of mature yield reached at month `t` (0-100), independent
    of the mature yield value itself (mirrors the mature_yield cancellation
    in yield_ramp_t95 above) -- i.e. yield_ramp_fraction(100, ramp_coef, t)
    expressed as a percent. Used ONLY by visualization.html's "기준 시점"
    (yield basis) toggle for its reference text (mirrored by render_html.py's
    JS `rampProgressPct`); calc.py's own sweep()/report.md never call this,
    since the monthly snapshot/crossover stay on mature_yield always."""
    return yield_ramp_fraction(100.0, ramp_coef, t) * 100.0


def yield_ramp_t95(ramp_coef: float) -> float:
    """Months elapsed (since THIS line's/recipe's own production start)
    until yield reaches 95% of ITS OWN mature yield. Solving
    mature*(1-exp(-k*t95)) = 0.95*mature for t95 gives t95 = ln(20)/k --
    mature_yield cancels out entirely, so t95 depends ONLY on ramp_coef.
    t=0..t95 is that line's/recipe's own "ER (engineering-run)/qualification
    period" (see module docstring)."""
    return math.log(20.0) / ramp_coef


def cumulative_ramp_bit_per_wafer(
    mature_yield_pct: float, ramp_coef: float, density: float, gross_die: float, active_months: float
) -> float:
    """Sum of bit-per-wafer over production months t=1..active_months
    (rounded to the nearest whole month), each month's yield computed from
    its own elapsed time via yield_ramp_fraction -- the actual month-by-month
    walk the cumulative bit totals use instead of a flat
    monthly_bit_total * active_months multiplication."""
    months = int(round(active_months))
    total = 0.0
    for t in range(1, months + 1):
        total += density * gross_die * yield_ramp_fraction(mature_yield_pct, ramp_coef, t)
    return total


def line_ramp_stats(mature_yield_pct: float, ramp_coef: float, density: float, gross_die: float) -> dict[str, float]:
    """Precompute this line's/recipe's own t95 (months to reach 95% of
    mature yield) and its cumulative bit-per-wafer over the two cumulative
    windows (1-year, 5-year) -- both over the FULL window and over just its
    own ER period (t=1..min(t95, window)). None of this depends on the
    QLC:TLC ratio, so it's computed once per line/recipe and reused across
    every sweep row (see sweep()), which needs only ONE more multiply/
    subtract per row to split a wafer count's cumulative bit into a total
    and a sale-only figure -- no per-row month-by-month loop required."""
    t95 = yield_ramp_t95(ramp_coef)

    def bpw(months: float) -> float:
        return cumulative_ramp_bit_per_wafer(mature_yield_pct, ramp_coef, density, gross_die, months)

    return {
        "t95": t95,
        "bpw_1y": bpw(ONE_YEAR_MONTHS),
        "bpw_5y": bpw(FIVE_YEAR_MONTHS),
        "bpw_er_1y": bpw(min(t95, ONE_YEAR_MONTHS)),
        "bpw_er_5y": bpw(min(t95, FIVE_YEAR_MONTHS)),
    }


def capex_rate_per_wafer(capex_per_10k_wafer: float) -> float:
    """`*_capex_per_wafer` fields are entered as cost per 10,000 wafers."""
    return capex_per_10k_wafer / WAFER_BATCH_FOR_CAPEX


def bit_total_gb(bit_total: float) -> float:
    """Raw bit totals are Gb-denominated; convert to GB for display/output."""
    return bit_total / GB_PER_GIGABIT


def cost_per_gb_eokwon_to_cent(cost_per_gb_eokwon: float, exchange_rate_krw_per_usd: float) -> float:
    """Convert a cost/GB figure, assumed already denominated in 억원 (the
    project's currency_unit convention), into cent/GB -- for
    visualization.html's Cost chart y-axis ONLY. 억원 -> 원 (x100,000,000),
    원 -> 달러 (/exchange_rate), 달러 -> cent (x100). NOT applied to
    cost_mode == "direct" values, which are already cent/GB."""
    if not (exchange_rate_krw_per_usd > 0):
        return float("inf")
    usd_per_gb = cost_per_gb_eokwon * WON_PER_EOKWON / exchange_rate_krw_per_usd
    return usd_per_gb * CENT_PER_USD


def combo_dev_cost(p: dict[str, float | str]) -> float:
    """One-time dev cost: headcount + mask ONLY (see module docstring for
    why the old ER-wafer cost term was removed, not just zeroed)."""
    return (
        p["combo_headcount"] * p["coef_cost_per_headcount"]
        + p["combo_mask_count"] * p["coef_cost_per_mask"]
    )


def dedicated_dev_cost(p: dict[str, float | str]) -> float:
    return (
        p["dedicated_headcount"] * p["coef_cost_per_headcount"]
        + p["dedicated_mask_count"] * p["coef_cost_per_mask"]
    )


def t95_months(p: dict[str, float | str]) -> dict[str, float]:
    """Each of the four lines'/recipes' own t95 (months to 95% of their own
    mature yield) -- ratio-independent, depends only on each *_yield_ramp_coef."""
    return {
        "qlc": yield_ramp_t95(p["qlc_yield_ramp_coef"]),
        "tlc": yield_ramp_t95(p["tlc_yield_ramp_coef"]),
        "combo_qlc": yield_ramp_t95(p["combo_qlc_yield_ramp_coef"]),
        "combo_tlc": yield_ramp_t95(p["combo_tlc_yield_ramp_coef"]),
    }


def sweep(p: dict[str, float | str], ratio_step: int) -> list[dict[str, float]]:
    bpw_combo_qlc = bit_per_wafer(p["combo_qlc_density"], p["combo_gross_die"], yield_fraction(p["combo_qlc_mature_yield"]))
    bpw_combo_tlc = bit_per_wafer(p["combo_tlc_density"], p["combo_gross_die"], yield_fraction(p["combo_tlc_mature_yield"]))
    bpw_ded_qlc = bit_per_wafer(p["qlc_density"], p["qlc_gross_die"], yield_fraction(p["qlc_mature_yield"]))
    bpw_ded_tlc = bit_per_wafer(p["tlc_density"], p["tlc_gross_die"], yield_fraction(p["tlc_mature_yield"]))

    combo_dev = combo_dev_cost(p)
    dedicated_dev = dedicated_dev_cost(p)

    # Per-line/recipe ramp stats (t95 + cumulative bit-per-wafer over both
    # cumulative windows, full window and ER-period-only) -- independent of
    # the ratio, computed once and reused across every row below.
    stats_combo_qlc = line_ramp_stats(p["combo_qlc_mature_yield"], p["combo_qlc_yield_ramp_coef"], p["combo_qlc_density"], p["combo_gross_die"])
    stats_combo_tlc = line_ramp_stats(p["combo_tlc_mature_yield"], p["combo_tlc_yield_ramp_coef"], p["combo_tlc_density"], p["combo_gross_die"])
    stats_ded_qlc = line_ramp_stats(p["qlc_mature_yield"], p["qlc_yield_ramp_coef"], p["qlc_density"], p["qlc_gross_die"])
    stats_ded_tlc = line_ramp_stats(p["tlc_mature_yield"], p["tlc_yield_ramp_coef"], p["tlc_density"], p["tlc_gross_die"])

    def window_totals(
        wafer_qlc: float, wafer_tlc: float, er_rate: float,
        stats_qlc: dict[str, float], stats_tlc: dict[str, float], window_key: str,
    ) -> tuple[float, float]:
        """Total bit (unchanged formula/value) and sale-only bit (total minus
        the bit the ER-consumed wafers would have produced) for one scenario
        over one cumulative window ("1y" or "5y"), summing the QLC-recipe/
        line and TLC-recipe/line contributions."""
        qlc_total = wafer_qlc * stats_qlc["bpw_" + window_key]
        tlc_total = wafer_tlc * stats_tlc["bpw_" + window_key]
        qlc_er_wafers = min(er_rate, wafer_qlc)
        tlc_er_wafers = min(er_rate, wafer_tlc)
        qlc_sale = qlc_total - qlc_er_wafers * stats_qlc["bpw_er_" + window_key]
        tlc_sale = tlc_total - tlc_er_wafers * stats_tlc["bpw_er_" + window_key]
        return qlc_total + tlc_total, qlc_sale + tlc_sale

    def row_at(r: int) -> dict[str, float]:
        qlc_share, tlc_share = r / 100.0, (100 - r) / 100.0

        # Each line sweeps ITS OWN 100%-utilization max capa by the ratio —
        # dedicated's two lines and combo's two recipe-modes are separate
        # investments, not shares of one fab-wide pool. wafer_total never
        # changes because of ER wafers -- ER wafers are carved OUT of it,
        # not added on top (see module docstring).
        wafer_qlc_dedicated = p["qlc_max_capa"] * qlc_share
        wafer_tlc_dedicated = p["tlc_max_capa"] * tlc_share
        wafer_qlc_combo = p["combo_qlc_max_capa"] * qlc_share
        wafer_tlc_combo = p["combo_tlc_max_capa"] * tlc_share

        combo_bit = wafer_qlc_combo * bpw_combo_qlc + wafer_tlc_combo * bpw_combo_tlc
        combo_cost = capex_rate_per_wafer(p["combo_capex_per_wafer"]) * (wafer_qlc_combo + wafer_tlc_combo) + combo_dev

        dedicated_bit = wafer_qlc_dedicated * bpw_ded_qlc + wafer_tlc_dedicated * bpw_ded_tlc
        dedicated_cost = (
            capex_rate_per_wafer(p["qlc_capex_per_wafer"]) * wafer_qlc_dedicated
            + capex_rate_per_wafer(p["tlc_capex_per_wafer"]) * wafer_tlc_dedicated
            + dedicated_dev
        )

        combo_bit_gb = bit_total_gb(combo_bit)
        dedicated_bit_gb = bit_total_gb(dedicated_bit)

        # Cumulative (1-year/5-year) totals. Cost does NOT depend on yield
        # (paid per wafer processed), so it stays a flat monthly rate times
        # the FULL window length (no development-months skip anymore), plus
        # the one-time dev_cost added ONCE. Bit DOES depend on yield, and
        # yield ramps up over time, so it's an actual month-by-month sum
        # (via line_ramp_stats/window_totals above) -- both a TOTAL figure
        # (unchanged formula) and a NEW sale-only figure.
        combo_monthly_wafer_cost = combo_cost - combo_dev
        dedicated_monthly_wafer_cost = dedicated_cost - dedicated_dev

        five_year_combo_bit, five_year_combo_sale_bit = window_totals(
            wafer_qlc_combo, wafer_tlc_combo, p["er_wafer_combo"], stats_combo_qlc, stats_combo_tlc, "5y"
        )
        one_year_combo_bit, one_year_combo_sale_bit = window_totals(
            wafer_qlc_combo, wafer_tlc_combo, p["er_wafer_combo"], stats_combo_qlc, stats_combo_tlc, "1y"
        )
        five_year_dedicated_bit, five_year_dedicated_sale_bit = window_totals(
            wafer_qlc_dedicated, wafer_tlc_dedicated, p["er_wafer_dedicated"], stats_ded_qlc, stats_ded_tlc, "5y"
        )
        one_year_dedicated_bit, one_year_dedicated_sale_bit = window_totals(
            wafer_qlc_dedicated, wafer_tlc_dedicated, p["er_wafer_dedicated"], stats_ded_qlc, stats_ded_tlc, "1y"
        )

        five_year_combo_cost = combo_monthly_wafer_cost * FIVE_YEAR_MONTHS + combo_dev
        one_year_combo_cost = combo_monthly_wafer_cost * ONE_YEAR_MONTHS + combo_dev
        five_year_dedicated_cost = dedicated_monthly_wafer_cost * FIVE_YEAR_MONTHS + dedicated_dev
        one_year_dedicated_cost = dedicated_monthly_wafer_cost * ONE_YEAR_MONTHS + dedicated_dev

        five_year_combo_bit_gb = bit_total_gb(five_year_combo_bit)
        five_year_combo_sale_bit_gb = bit_total_gb(five_year_combo_sale_bit)
        one_year_combo_bit_gb = bit_total_gb(one_year_combo_bit)
        one_year_combo_sale_bit_gb = bit_total_gb(one_year_combo_sale_bit)
        five_year_dedicated_bit_gb = bit_total_gb(five_year_dedicated_bit)
        five_year_dedicated_sale_bit_gb = bit_total_gb(five_year_dedicated_sale_bit)
        one_year_dedicated_bit_gb = bit_total_gb(one_year_dedicated_bit)
        one_year_dedicated_sale_bit_gb = bit_total_gb(one_year_dedicated_sale_bit)

        return {
            "qlc_ratio": r,
            "tlc_ratio": 100 - r,
            "wafer_qlc_dedicated": wafer_qlc_dedicated,
            "wafer_tlc_dedicated": wafer_tlc_dedicated,
            "wafer_qlc_combo": wafer_qlc_combo,
            "wafer_tlc_combo": wafer_tlc_combo,
            "combo_bit_total": combo_bit,
            "combo_cost_total": combo_cost,
            "combo_cost_per_bit": (combo_cost / combo_bit) if combo_bit > 0 else float("inf"),
            "dedicated_bit_total": dedicated_bit,
            "dedicated_cost_total": dedicated_cost,
            "dedicated_cost_per_bit": (dedicated_cost / dedicated_bit) if dedicated_bit > 0 else float("inf"),
            # GB-converted display fields (1 GB = 8 Gb) — used by charts/report,
            # never by the crossover comparison (ratio is unaffected by a
            # shared /8 scale factor on both scenarios).
            "combo_bit_total_gb": combo_bit_gb,
            "dedicated_bit_total_gb": dedicated_bit_gb,
            "combo_cost_per_gb": (combo_cost / combo_bit_gb) if combo_bit_gb > 0 else float("inf"),
            "dedicated_cost_per_gb": (dedicated_cost / dedicated_bit_gb) if dedicated_bit_gb > 0 else float("inf"),
            # 5-year (60-month) cumulative fields. *_bit_total is the TOTAL
            # (sale + ER) figure, formula unchanged from before this refine.
            # *_sale_bit_total is NEW: total minus the bit the ER-consumed
            # wafers would have produced during their line's/recipe's own
            # ER period (t95).
            "five_year_combo_bit_total": five_year_combo_bit,
            "five_year_combo_bit_total_gb": five_year_combo_bit_gb,
            "five_year_combo_sale_bit_total": five_year_combo_sale_bit,
            "five_year_combo_sale_bit_total_gb": five_year_combo_sale_bit_gb,
            "five_year_combo_cost_total": five_year_combo_cost,
            "five_year_combo_cost_per_bit": (
                five_year_combo_cost / five_year_combo_bit if five_year_combo_bit > 0 else float("inf")
            ),
            "five_year_combo_cost_per_gb": (
                five_year_combo_cost / five_year_combo_bit_gb if five_year_combo_bit_gb > 0 else float("inf")
            ),
            "five_year_dedicated_bit_total": five_year_dedicated_bit,
            "five_year_dedicated_bit_total_gb": five_year_dedicated_bit_gb,
            "five_year_dedicated_sale_bit_total": five_year_dedicated_sale_bit,
            "five_year_dedicated_sale_bit_total_gb": five_year_dedicated_sale_bit_gb,
            "five_year_dedicated_cost_total": five_year_dedicated_cost,
            "five_year_dedicated_cost_per_bit": (
                five_year_dedicated_cost / five_year_dedicated_bit if five_year_dedicated_bit > 0 else float("inf")
            ),
            "five_year_dedicated_cost_per_gb": (
                five_year_dedicated_cost / five_year_dedicated_bit_gb if five_year_dedicated_bit_gb > 0 else float("inf")
            ),
            # 1-year (12-month) cumulative fields — NEW, computed the exact
            # same way as the 5-year fields above, just over ONE_YEAR_MONTHS.
            "one_year_combo_bit_total": one_year_combo_bit,
            "one_year_combo_bit_total_gb": one_year_combo_bit_gb,
            "one_year_combo_sale_bit_total": one_year_combo_sale_bit,
            "one_year_combo_sale_bit_total_gb": one_year_combo_sale_bit_gb,
            "one_year_combo_cost_total": one_year_combo_cost,
            "one_year_combo_cost_per_bit": (
                one_year_combo_cost / one_year_combo_bit if one_year_combo_bit > 0 else float("inf")
            ),
            "one_year_combo_cost_per_gb": (
                one_year_combo_cost / one_year_combo_bit_gb if one_year_combo_bit_gb > 0 else float("inf")
            ),
            "one_year_dedicated_bit_total": one_year_dedicated_bit,
            "one_year_dedicated_bit_total_gb": one_year_dedicated_bit_gb,
            "one_year_dedicated_sale_bit_total": one_year_dedicated_sale_bit,
            "one_year_dedicated_sale_bit_total_gb": one_year_dedicated_sale_bit_gb,
            "one_year_dedicated_cost_total": one_year_dedicated_cost,
            "one_year_dedicated_cost_per_bit": (
                one_year_dedicated_cost / one_year_dedicated_bit if one_year_dedicated_bit > 0 else float("inf")
            ),
            "one_year_dedicated_cost_per_gb": (
                one_year_dedicated_cost / one_year_dedicated_bit_gb if one_year_dedicated_bit_gb > 0 else float("inf")
            ),
        }

    rows = []
    r = 0
    while r <= 100:
        rows.append(row_at(r))
        r += ratio_step
    if rows[-1]["qlc_ratio"] != 100:
        rows.append(row_at(100))
    return rows


def find_crossover(rows: list[dict[str, float]]) -> dict:
    """First ratio (scanning from qlc_ratio=0, i.e. all-TLC) where combo's
    cost/bit is at or below dedicated's. Combo is typically most TLC-efficient
    near its QLC-native mode, so this is usually also the ratio below which
    (more TLC demand) dedicated wins and above which (more QLC demand / less
    TLC demand) combo wins."""
    better = [row for row in rows if row["combo_cost_per_bit"] <= row["dedicated_cost_per_bit"]]
    if not better:
        return {"exists": False}
    row = better[0]
    return {
        "exists": True,
        "qlc_ratio": row["qlc_ratio"],
        "tlc_ratio": row["tlc_ratio"],
        "combo_cost_per_bit": row["combo_cost_per_bit"],
        "dedicated_cost_per_bit": row["dedicated_cost_per_bit"],
    }


def full_buildout(p: dict[str, float | str]) -> dict:
    """Ratio-independent total investment if each scenario built every one of
    its lines out to its own 100%-utilization max capacity. Dedicated sums
    its two independent lines; combo is one physical line, represented by
    combo_qlc_max_capa (see COMBO_FULL_CAPEX_ASSUMPTION). Only meaningful
    when cost_mode == "model" — the display layer shows this as text, not a
    chart, and reports it as not-applicable in "direct" cost mode."""
    dedicated_capex = (
        capex_rate_per_wafer(p["qlc_capex_per_wafer"]) * p["qlc_max_capa"]
        + capex_rate_per_wafer(p["tlc_capex_per_wafer"]) * p["tlc_max_capa"]
        + dedicated_dev_cost(p)
    )
    combo_capex = (
        capex_rate_per_wafer(p["combo_capex_per_wafer"]) * p["combo_qlc_max_capa"]
        + combo_dev_cost(p)
    )
    return {
        "combo": combo_capex,
        "dedicated": dedicated_capex,
        "combo_representative_capa_field": "combo_qlc_max_capa",
        "combo_assumption": COMBO_FULL_CAPEX_ASSUMPTION,
    }


def yield_ramp_curves(p: dict[str, float | str]) -> dict:
    """Fixed reference ramp curves (t=0..RAMP_CHART_MONTHS) for the two
    yield-ramp charts — always shown regardless of the QLC:TLC ratio
    slider, purely so mature_yield/ramp_coef can be tuned by eye."""
    return {
        "qlc_dedicated": yield_ramp_curve(p["qlc_mature_yield"], p["qlc_yield_ramp_coef"]),
        "qlc_combo": yield_ramp_curve(p["combo_qlc_mature_yield"], p["combo_qlc_yield_ramp_coef"]),
        "tlc_dedicated": yield_ramp_curve(p["tlc_mature_yield"], p["tlc_yield_ramp_coef"]),
        "tlc_combo": yield_ramp_curve(p["combo_tlc_mature_yield"], p["combo_tlc_yield_ramp_coef"]),
    }


def run(params_path: Path, outputs_dir: Path, ratio_step: int, is_sample: bool = False) -> dict:
    p = load_params(params_path)
    ratio_step = int(p.get("ratio_step", ratio_step)) if isinstance(p.get("ratio_step"), str) else ratio_step
    rows = sweep(p, ratio_step)
    crossover = find_crossover(rows)

    best_combo_bit = max(rows, key=lambda row: row["combo_bit_total"])
    best_combo_cost = min(rows, key=lambda row: row["combo_cost_per_bit"])
    best_dedicated_bit = max(rows, key=lambda row: row["dedicated_bit_total"])
    best_dedicated_cost = min(rows, key=lambda row: row["dedicated_cost_per_bit"])

    outputs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = outputs_dir / "sweep.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    dev_cost = {
        "combo": combo_dev_cost(p),
        "dedicated": dedicated_dev_cost(p),
    }
    buildout = full_buildout(p)
    cost_mode = p["cost_mode"]
    direct_cost_per_gb = {
        "combo": float(p["combo_direct_cost_per_gb"]),
        "dedicated": float(p["dedicated_direct_cost_per_gb"]),
    }
    t95 = t95_months(p)

    payload = {
        "params": {k: v for k, v in p.items()},
        "sweep": rows,
        "crossover": crossover,
        "dev_cost": dev_cost,
        "full_buildout": buildout,
        "yield_ramp_curves": yield_ramp_curves(p),
        "t95_months": t95,
        "er_wafer_rate_assumption": ER_WAFER_RATE_ASSUMPTION,
        "cost_mode": cost_mode,
        "direct_cost_per_gb": direct_cost_per_gb,
        "best_combo_bit_production": best_combo_bit,
        "best_combo_cost_per_bit": best_combo_cost,
        "best_dedicated_bit_production": best_dedicated_bit,
        "best_dedicated_cost_per_bit": best_dedicated_cost,
        "currency_unit": p["currency_unit"],
        "bit_unit": p["bit_unit"],
        "is_sample": is_sample,
    }
    (outputs_dir / "sweep.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (outputs_dir / "summary.json").write_text(
        json.dumps({
            "crossover": crossover,
            "dev_cost": dev_cost,
            "full_buildout": buildout,
            "t95_months": t95,
            "er_wafer_rate_assumption": ER_WAFER_RATE_ASSUMPTION,
            "cost_mode": cost_mode,
            "direct_cost_per_gb": direct_cost_per_gb,
            "best_combo_bit_production": best_combo_bit,
            "best_combo_cost_per_bit": best_combo_cost,
            "best_dedicated_bit_production": best_dedicated_bit,
            "best_dedicated_cost_per_bit": best_dedicated_cost,
            "currency_unit": p["currency_unit"],
            "bit_unit": p["bit_unit"],
            "is_sample": is_sample,
        }, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("params_file")
    ap.add_argument("outputs_dir")
    ap.add_argument("--step", type=int, default=5, help="ratio sweep step in percent (default 5)")
    ap.add_argument("--sample", action="store_true", help="mark this run's payload as sample/demo data")
    args = ap.parse_args()

    params_path = Path(args.params_file)
    outputs_dir = Path(args.outputs_dir)

    if not params_path.exists():
        print(f"error: params file not found: {params_path}", file=sys.stderr)
        return 1

    try:
        payload = run(params_path, outputs_dir, args.step, is_sample=args.sample)
    except ParamsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(json.dumps({
        "crossover": payload["crossover"],
        "dev_cost": payload["dev_cost"],
        "full_buildout": payload["full_buildout"],
        "t95_months": payload["t95_months"],
        "cost_mode": payload["cost_mode"],
        "sweep_rows": len(payload["sweep"]),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
