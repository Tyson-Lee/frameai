import math
import re
import sys
import tempfile
from pathlib import Path

HELPERS_DIR = Path(__file__).resolve().parents[1] / "skills" / "qlc-tlc-bit-cost-calculator" / "helpers"
SAMPLE = Path(__file__).resolve().parents[1] / "automations" / "qlc-tlc-bit-cost-calculator" / "samples" / "sample-1.txt"
SAMPLE2 = Path(__file__).resolve().parents[1] / "automations" / "qlc-tlc-bit-cost-calculator" / "samples" / "sample-2.txt"
sys.path.insert(0, str(HELPERS_DIR))

import calc  # noqa: E402
import render_html  # noqa: E402


def _extract_initial_payload(html: str) -> dict:
    """visualization.html embeds its seed data as `var INITIAL_PAYLOAD = {...};`
    inside `<script id="payload">` -- a JS object literal (pretty-printed,
    with trailing `// label` comments on "params" keys), not raw JSON, so it
    can be hand-edited in a plain text editor. Strip the `//` comments and
    parse the rest as JSON to get the payload back out for assertions."""
    import json

    match = re.search(
        r'<script id="payload">\s*var INITIAL_PAYLOAD = (.*?);\s*</script>',
        html, re.S,
    )
    assert match is not None, "INITIAL_PAYLOAD script block not found"
    raw = re.sub(r"//[^\n]*", "", match.group(1))
    return json.loads(raw)


class TestParseParams:
    def test_parses_key_value_and_skips_comments(self):
        text = "# comment\nfoo=1\n\nbar = 2  # inline comment\n"
        params = calc.parse_params(text)
        assert params == {"foo": "1", "bar": "2"}

    def test_missing_equals_raises(self):
        try:
            calc.parse_params("not_a_kv_line")
            assert False, "expected ParamsError"
        except calc.ParamsError:
            pass


class TestLoadParams:
    def test_missing_required_key_raises(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "params.txt"
            p.write_text("qlc_capex_per_wafer=1\n")
            try:
                calc.load_params(p)
                assert False, "expected ParamsError"
            except calc.ParamsError as e:
                assert "missing required keys" in str(e)

    def test_sample_file_loads(self):
        params = calc.load_params(SAMPLE)
        assert params["qlc_capex_per_wafer"] == 6200
        assert params["currency_unit"] == "억원"

    def test_only_the_two_shared_dev_cost_coefficients_remain(self):
        """The old step-tuning coefficient system (coef_capex_cost/
        coef_density_bit/coef_gross_die_bit/coef_wafer_bit/coef_step_cost) is
        still gone; only the two flat, shared dev-cost conversion rates
        introduced for headcount/mask cost remain."""
        coef_keys = {k for k in calc.REQUIRED_KEYS if k.startswith("coef_")}
        assert coef_keys == {"coef_cost_per_headcount", "coef_cost_per_mask"}
        assert not any("step" in k for k in calc.REQUIRED_KEYS)

    def test_required_keys_use_mature_yield_ramp_pairs_not_flat_yield(self):
        """The four flat *_yield fields were replaced by *_mature_yield /
        *_yield_ramp_coef pairs -- 4 fields became 8, required key count
        went 26 -> 30."""
        assert "qlc_yield" not in calc.REQUIRED_KEYS
        assert "tlc_yield" not in calc.REQUIRED_KEYS
        assert "combo_qlc_yield" not in calc.REQUIRED_KEYS
        assert "combo_tlc_yield" not in calc.REQUIRED_KEYS
        for prefix in ("qlc", "tlc", "combo_qlc", "combo_tlc"):
            assert f"{prefix}_mature_yield" in calc.REQUIRED_KEYS
            assert f"{prefix}_yield_ramp_coef" in calc.REQUIRED_KEYS
        assert len(calc.REQUIRED_KEYS) == 30

    def test_display_settings_default_when_absent(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "params.txt"
            required_text = "\n".join(f"{k}=1" for k in calc.REQUIRED_KEYS)
            p.write_text(required_text)
            params = calc.load_params(p)
            assert params["currency_unit"] == "cost unit"
            assert params["bit_unit"] == "bit unit"
            assert params["ratio_step"] == "5"
            assert params["exchange_rate_krw_per_usd"] == "1300"
            assert params["cost_mode"] == "model"
            assert params["combo_direct_cost_per_gb"] == "0"
            assert params["dedicated_direct_cost_per_gb"] == "0"

    def test_dev_ramp_months_no_longer_an_optional_key(self):
        """dev_ramp_months was removed outright -- each line's/recipe's own
        t95 (see TestYieldRampT95) replaces the shared ramp-months
        assumption entirely, so there is no default to fall back to."""
        assert "dev_ramp_months" not in calc.OPTIONAL_STR_DEFAULTS


class TestBitPerWafer:
    def test_multiplies_density_gross_die_yield(self):
        assert calc.bit_per_wafer(10, 5, 0.5) == 10 * 5 * 0.5


class TestYieldRamp:
    """Normalized Exponential Saturation: yield_fraction(t) = mature_yield_fraction
    * (1 - exp(-ramp_coef * t)), t = months since THIS line/recipe's own
    production start (t=0)."""

    def test_yield_ramp_fraction_matches_formula(self):
        got = calc.yield_ramp_fraction(82, 0.15, 12)
        expected = calc.yield_fraction(82) * (1 - math.exp(-0.15 * 12))
        assert got == expected

    def test_yield_ramp_fraction_is_zero_at_t_zero(self):
        assert calc.yield_ramp_fraction(82, 0.15, 0) == 0

    def test_yield_ramp_fraction_approaches_mature_yield_as_t_grows(self):
        near_mature = calc.yield_ramp_fraction(82, 0.15, 10_000)
        assert math.isclose(near_mature, calc.yield_fraction(82), rel_tol=1e-9)

    def test_larger_ramp_coef_reaches_mature_yield_faster(self):
        slow = calc.yield_ramp_fraction(82, 0.05, 12)
        fast = calc.yield_ramp_fraction(82, 0.3, 12)
        assert fast > slow

    def test_yield_ramp_curve_spans_zero_to_ramp_chart_months(self):
        curve = calc.yield_ramp_curve(82, 0.15)
        assert curve[0]["month"] == 0
        assert curve[-1]["month"] == calc.RAMP_CHART_MONTHS
        assert len(curve) == calc.RAMP_CHART_MONTHS + 1
        assert curve[0]["yield_pct"] == 0
        assert curve[-1]["yield_pct"] < 82  # never fully reaches mature yield

    def test_cumulative_ramp_bit_per_wafer_is_less_than_naive_monthly_times_months(self):
        """The whole point of the ramp: early months produce less than the
        mature (fully-ramped) rate, so summing the actual per-month yield
        must be strictly less than density*gross_die*mature_yield*months."""
        density, gross_die, mature_yield, ramp_coef, months = 48.0, 520.0, 82.0, 0.15, 54.0
        cumulative = calc.cumulative_ramp_bit_per_wafer(mature_yield, ramp_coef, density, gross_die, months)
        naive = density * gross_die * calc.yield_fraction(mature_yield) * months
        assert 0 < cumulative < naive

    def test_cumulative_ramp_bit_per_wafer_approaches_naive_as_ramp_coef_grows(self):
        """An (unrealistically) huge ramp_coef means the line is at mature
        yield from month 1 onward, so the sum should converge to the naive
        monthly*months figure."""
        density, gross_die, mature_yield, months = 48.0, 520.0, 82.0, 54.0
        cumulative = calc.cumulative_ramp_bit_per_wafer(mature_yield, 50.0, density, gross_die, months)
        naive = density * gross_die * calc.yield_fraction(mature_yield) * months
        assert math.isclose(cumulative, naive, rel_tol=1e-6)


class TestYieldRampT95:
    """t95 = ln(20)/ramp_coef -- the month a line's/recipe's own yield
    reaches 95% of ITS OWN mature yield, independent of the mature_yield
    value itself. t=0..t95 is that line's/recipe's own ER period (see
    calc.py module docstring)."""

    def test_t95_matches_closed_form(self):
        assert calc.yield_ramp_t95(0.15) == math.log(20.0) / 0.15

    def test_t95_actually_reaches_95_percent_of_mature_yield(self):
        for mature, coef in [(82.0, 0.15), (50.0, 0.3), (95.0, 0.05)]:
            t95 = calc.yield_ramp_t95(coef)
            got = calc.yield_ramp_fraction(mature, coef, t95)
            expected = 0.95 * calc.yield_fraction(mature)
            assert math.isclose(got, expected, rel_tol=1e-9)

    def test_t95_is_independent_of_mature_yield(self):
        coef = 0.2
        t95_a = calc.yield_ramp_t95(coef)
        # yield_ramp_t95 doesn't even take mature_yield as an argument --
        # confirm two different mature yields at the same ramp_coef hit 95%
        # of THEIR OWN mature yield at the exact same t95.
        for mature in (10.0, 50.0, 99.0):
            got = calc.yield_ramp_fraction(mature, coef, t95_a)
            assert math.isclose(got, 0.95 * calc.yield_fraction(mature), rel_tol=1e-9)

    def test_larger_ramp_coef_means_smaller_t95(self):
        assert calc.yield_ramp_t95(0.3) < calc.yield_ramp_t95(0.1)


class TestDevCost:
    def test_combo_dev_cost_is_headcount_and_mask_only(self):
        """The old ER-wafer cost term is gone outright -- wafer_total *
        capex_rate_per_wafer (unchanged) already pays for every wafer
        processed, ER or not, so a separate ER-wafer cost line would double
        count."""
        params = calc.load_params(SAMPLE)
        expected = (
            params["combo_headcount"] * params["coef_cost_per_headcount"]
            + params["combo_mask_count"] * params["coef_cost_per_mask"]
        )
        assert calc.combo_dev_cost(params) == expected

    def test_dedicated_dev_cost_is_headcount_and_mask_only(self):
        params = calc.load_params(SAMPLE)
        expected = (
            params["dedicated_headcount"] * params["coef_cost_per_headcount"]
            + params["dedicated_mask_count"] * params["coef_cost_per_mask"]
        )
        assert calc.dedicated_dev_cost(params) == expected

    def test_dev_cost_functions_ignore_er_wafer_rate_entirely(self):
        """Changing er_wafer_combo/er_wafer_dedicated must not move dev cost
        at all -- ER wafers now feed bit production (sale/ER split), not
        the one-time dev-cost model."""
        params = calc.load_params(SAMPLE)
        bumped = dict(params)
        bumped["er_wafer_combo"] = params["er_wafer_combo"] * 50
        bumped["er_wafer_dedicated"] = params["er_wafer_dedicated"] * 50
        assert calc.combo_dev_cost(bumped) == calc.combo_dev_cost(params)
        assert calc.dedicated_dev_cost(bumped) == calc.dedicated_dev_cost(params)

    def test_no_dedicated_er_cost_assumption_remains(self):
        """The old 50/50 ER-wafer-to-cost blend assumption is gone along
        with the cost term it justified."""
        assert not hasattr(calc, "DEDICATED_ER_ASSUMPTION")

    def test_er_wafer_rate_assumption_documents_independent_not_split_application(self):
        assert "er_wafer_combo" in calc.ER_WAFER_RATE_ASSUMPTION
        assert "er_wafer_dedicated" in calc.ER_WAFER_RATE_ASSUMPTION
        assert "not split" in calc.ER_WAFER_RATE_ASSUMPTION

    def test_capex_rate_per_wafer_divides_by_10000(self):
        assert calc.capex_rate_per_wafer(6200) == 0.62

    def test_yield_fraction_divides_by_100(self):
        assert calc.yield_fraction(82) == 0.82

    def test_bit_total_gb_divides_by_8(self):
        assert calc.bit_total_gb(80) == 10.0

    def test_cost_per_gb_eokwon_to_cent_matches_formula(self):
        # 1억원/GB @ 1300 원/달러 -> 100,000,000/1300 달러 -> *100 cent
        cent = calc.cost_per_gb_eokwon_to_cent(1.0, 1300.0)
        assert cent == (1.0 * 100_000_000 / 1300.0) * 100.0

    def test_cost_per_gb_eokwon_to_cent_scales_inversely_with_exchange_rate(self):
        low_rate = calc.cost_per_gb_eokwon_to_cent(1.0, 1000.0)
        high_rate = calc.cost_per_gb_eokwon_to_cent(1.0, 2000.0)
        assert low_rate == high_rate * 2


class TestSweep:
    def test_each_line_sweeps_its_own_independent_max_capa(self):
        """dedicated's QLC/TLC lines and combo's QLC/TLC recipes each carry
        their OWN 100%-utilization max capa -- NOT a single shared fab-wide
        pool -- so wafer_*_dedicated and wafer_*_combo must scale off their
        own, independently-valued max_capa field at every ratio."""
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            assert row["wafer_qlc_dedicated"] == params["qlc_max_capa"] * row["qlc_ratio"] / 100.0
            assert row["wafer_tlc_dedicated"] == params["tlc_max_capa"] * row["tlc_ratio"] / 100.0
            assert row["wafer_qlc_combo"] == params["combo_qlc_max_capa"] * row["qlc_ratio"] / 100.0
            assert row["wafer_tlc_combo"] == params["combo_tlc_max_capa"] * row["tlc_ratio"] / 100.0

    def test_independent_max_capa_values_need_not_match(self):
        """The whole point of the four separate max_capa fields: dedicated's
        two lines (and combo's two recipes) are separate investments, so
        their 100%-max capacities can differ. SAMPLE is deliberately crafted
        with four different values -- assert they really are different and
        that wafer allocation reflects each one on its own, not some blended
        or shared total."""
        params = calc.load_params(SAMPLE)
        capas = {
            params["qlc_max_capa"], params["tlc_max_capa"],
            params["combo_qlc_max_capa"], params["combo_tlc_max_capa"],
        }
        assert len(capas) > 1, "sample params should exercise independent (non-equal) max_capa values"

        rows = calc.sweep(params, ratio_step=50)
        half = next(r for r in rows if r["qlc_ratio"] == 50)
        assert half["wafer_qlc_dedicated"] == params["qlc_max_capa"] * 0.5
        assert half["wafer_tlc_dedicated"] == params["tlc_max_capa"] * 0.5
        assert half["wafer_qlc_combo"] == params["combo_qlc_max_capa"] * 0.5
        assert half["wafer_tlc_combo"] == params["combo_tlc_max_capa"] * 0.5

    def test_sweep_endpoints_match_single_recipe_capacity(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        zero = next(r for r in rows if r["qlc_ratio"] == 0)
        hundred = next(r for r in rows if r["qlc_ratio"] == 100)
        assert zero["wafer_qlc_dedicated"] == 0
        assert zero["wafer_qlc_combo"] == 0
        assert hundred["wafer_tlc_dedicated"] == 0
        assert hundred["wafer_tlc_combo"] == 0

        bpw_combo_tlc = params["combo_tlc_density"] * params["combo_gross_die"] * calc.yield_fraction(params["combo_tlc_mature_yield"])
        combo_dev = calc.combo_dev_cost(params)
        assert zero["combo_bit_total"] == params["combo_tlc_max_capa"] * bpw_combo_tlc
        assert zero["combo_cost_total"] == calc.capex_rate_per_wafer(params["combo_capex_per_wafer"]) * params["combo_tlc_max_capa"] + combo_dev

        bpw_ded_qlc = params["qlc_density"] * params["qlc_gross_die"] * calc.yield_fraction(params["qlc_mature_yield"])
        dedicated_dev = calc.dedicated_dev_cost(params)
        assert hundred["dedicated_bit_total"] == params["qlc_max_capa"] * bpw_ded_qlc
        assert hundred["dedicated_cost_total"] == calc.capex_rate_per_wafer(params["qlc_capex_per_wafer"]) * params["qlc_max_capa"] + dedicated_dev

    def test_dedicated_cost_total_varies_with_ratio(self):
        """Dedicated cost depends on the ratio because qlc_capex_per_wafer !=
        tlc_capex_per_wafer AND qlc_max_capa != tlc_max_capa."""
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=50)
        costs = {r["dedicated_cost_total"] for r in rows}
        assert len(costs) > 1

    def test_combo_cost_total_varies_with_ratio(self):
        """Unlike the old shared-pool model where combo's total wafer count
        was ratio-invariant, combo_qlc_max_capa != combo_tlc_max_capa in
        SAMPLE means combo's total wafer count -- and therefore cost --
        now also moves with the ratio."""
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=50)
        costs = {r["combo_cost_total"] for r in rows}
        assert len(costs) > 1

    def test_dev_cost_applied_at_every_ratio_not_just_once(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        combo_dev = calc.combo_dev_cost(params)
        dedicated_dev = calc.dedicated_dev_cost(params)
        for row in rows:
            wafer_total_combo = calc.capex_rate_per_wafer(params["combo_capex_per_wafer"]) * (
                row["wafer_qlc_combo"] + row["wafer_tlc_combo"]
            )
            assert row["combo_cost_total"] == wafer_total_combo + combo_dev
            wafer_total_ded = (
                calc.capex_rate_per_wafer(params["qlc_capex_per_wafer"]) * row["wafer_qlc_dedicated"]
                + calc.capex_rate_per_wafer(params["tlc_capex_per_wafer"]) * row["wafer_tlc_dedicated"]
            )
            assert row["dedicated_cost_total"] == wafer_total_ded + dedicated_dev

    def test_sweep_always_includes_ratio_100(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=30)
        assert rows[-1]["qlc_ratio"] == 100

    def test_monthly_bit_uses_mature_yield_not_ramped_yield(self):
        """The monthly snapshot fields must be identical to what you'd get
        from a permanently fully-ramped line -- ramp_coef must not affect
        combo_bit_total / dedicated_bit_total at all."""
        params = calc.load_params(SAMPLE)
        rows_a = calc.sweep(params, ratio_step=50)

        params_different_ramp = dict(params)
        params_different_ramp["qlc_yield_ramp_coef"] = params["qlc_yield_ramp_coef"] * 5
        params_different_ramp["combo_qlc_yield_ramp_coef"] = params["combo_qlc_yield_ramp_coef"] * 5
        rows_b = calc.sweep(params_different_ramp, ratio_step=50)

        for a, b in zip(rows_a, rows_b):
            assert a["combo_bit_total"] == b["combo_bit_total"]
            assert a["dedicated_bit_total"] == b["dedicated_bit_total"]


class TestGbDisplayConversion:
    """1 GB = 8 Gb, applied ONLY at the display/output layer -- the raw Gb
    sweep fields (combo_bit_total etc.) and the crossover comparison must be
    completely unaffected by this conversion."""

    def test_bit_total_gb_fields_are_raw_bit_total_over_eight(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            assert row["combo_bit_total_gb"] == row["combo_bit_total"] / 8.0
            assert row["dedicated_bit_total_gb"] == row["dedicated_bit_total"] / 8.0

    def test_cost_per_gb_is_eight_times_cost_per_bit(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            if row["combo_bit_total"] > 0:
                assert row["combo_cost_per_gb"] == row["combo_cost_per_bit"] * 8.0
            if row["dedicated_bit_total"] > 0:
                assert row["dedicated_cost_per_gb"] == row["dedicated_cost_per_bit"] * 8.0

    def test_gb_scaling_does_not_change_which_scenario_wins(self):
        """A uniform /8 (or *8) scale factor applied to both scenarios must
        never flip a cost_per_bit comparison -- the crossover ratio derived
        from raw Gb data must still hold when compared in GB terms."""
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=5)
        for row in rows:
            bit_says_combo_wins = row["combo_cost_per_bit"] <= row["dedicated_cost_per_bit"]
            gb_says_combo_wins = row["combo_cost_per_gb"] <= row["dedicated_cost_per_gb"]
            assert bit_says_combo_wins == gb_says_combo_wins


class TestCumulativeWindows:
    """1-year (12-month) and 5-year (60-month) cumulative fields are
    display-layer derivations of the same sweep rows. Cost does NOT depend
    on yield (paid per wafer processed) so it's a flat monthly rate * the
    FULL window length + dev_cost added once -- there is no more shared
    "development months" skip (calc.active_production_months is gone; both
    windows start at production month 1). Bit DOES depend on yield, which
    ramps up over time, so it is an actual month-by-month sum over each
    line's/recipe's own ramp curve, split into a TOTAL figure (unchanged
    formula) and a NEW sale-only figure (see TestErWaferSaleSplit)."""

    def test_no_active_production_months_helper_remains(self):
        assert not hasattr(calc, "active_production_months")

    def test_window_constants(self):
        assert calc.ONE_YEAR_MONTHS == 12.0
        assert calc.FIVE_YEAR_MONTHS == 60.0

    def test_five_year_bit_total_matches_wafer_count_times_cumulative_ramp_bpw(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)

        ramp_combo_qlc = calc.cumulative_ramp_bit_per_wafer(
            params["combo_qlc_mature_yield"], params["combo_qlc_yield_ramp_coef"],
            params["combo_qlc_density"], params["combo_gross_die"], calc.FIVE_YEAR_MONTHS,
        )
        ramp_combo_tlc = calc.cumulative_ramp_bit_per_wafer(
            params["combo_tlc_mature_yield"], params["combo_tlc_yield_ramp_coef"],
            params["combo_tlc_density"], params["combo_gross_die"], calc.FIVE_YEAR_MONTHS,
        )
        ramp_ded_qlc = calc.cumulative_ramp_bit_per_wafer(
            params["qlc_mature_yield"], params["qlc_yield_ramp_coef"],
            params["qlc_density"], params["qlc_gross_die"], calc.FIVE_YEAR_MONTHS,
        )
        ramp_ded_tlc = calc.cumulative_ramp_bit_per_wafer(
            params["tlc_mature_yield"], params["tlc_yield_ramp_coef"],
            params["tlc_density"], params["tlc_gross_die"], calc.FIVE_YEAR_MONTHS,
        )

        for row in rows:
            expected_combo = row["wafer_qlc_combo"] * ramp_combo_qlc + row["wafer_tlc_combo"] * ramp_combo_tlc
            expected_dedicated = row["wafer_qlc_dedicated"] * ramp_ded_qlc + row["wafer_tlc_dedicated"] * ramp_ded_tlc
            assert row["five_year_combo_bit_total"] == expected_combo
            assert row["five_year_dedicated_bit_total"] == expected_dedicated

    def test_one_year_bit_total_matches_wafer_count_times_cumulative_ramp_bpw(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)

        ramp_ded_qlc = calc.cumulative_ramp_bit_per_wafer(
            params["qlc_mature_yield"], params["qlc_yield_ramp_coef"],
            params["qlc_density"], params["qlc_gross_die"], calc.ONE_YEAR_MONTHS,
        )
        ramp_ded_tlc = calc.cumulative_ramp_bit_per_wafer(
            params["tlc_mature_yield"], params["tlc_yield_ramp_coef"],
            params["tlc_density"], params["tlc_gross_die"], calc.ONE_YEAR_MONTHS,
        )
        for row in rows:
            expected_dedicated = row["wafer_qlc_dedicated"] * ramp_ded_qlc + row["wafer_tlc_dedicated"] * ramp_ded_tlc
            assert row["one_year_dedicated_bit_total"] == expected_dedicated

    def test_five_year_bit_total_is_less_than_naive_monthly_times_sixty(self):
        """The whole point of walking the ramp curve instead of a flat
        multiplication: early months produce less than the mature rate, so
        the real five-year bit total must be strictly less than the naive
        monthly_bit_total * 60 figure (for any ratio with nonzero
        production)."""
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            naive_combo = row["combo_bit_total"] * calc.FIVE_YEAR_MONTHS
            naive_dedicated = row["dedicated_bit_total"] * calc.FIVE_YEAR_MONTHS
            if row["combo_bit_total"] > 0:
                assert row["five_year_combo_bit_total"] < naive_combo
            if row["dedicated_bit_total"] > 0:
                assert row["five_year_dedicated_bit_total"] < naive_dedicated

    def test_one_year_bit_total_is_less_than_five_year_bit_total(self):
        """Both windows start at production month 1 and walk the same ramp
        curve -- 12 months of accumulation must be strictly less than 60
        months of it, for any ratio with nonzero production."""
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            if row["combo_bit_total"] > 0:
                assert row["one_year_combo_bit_total"] < row["five_year_combo_bit_total"]
            if row["dedicated_bit_total"] > 0:
                assert row["one_year_dedicated_bit_total"] < row["five_year_dedicated_bit_total"]

    def test_cost_total_excludes_dev_cost_from_the_monthly_multiplier(self):
        """N_year_cost_total = (monthly_cost - dev_cost) * N_MONTHS +
        dev_cost -- the one-time dev cost must be added exactly once, not
        scaled by the window length like the recurring wafer cost is."""
        params = calc.load_params(SAMPLE)
        combo_dev = calc.combo_dev_cost(params)
        dedicated_dev = calc.dedicated_dev_cost(params)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            expected_five_combo = (row["combo_cost_total"] - combo_dev) * calc.FIVE_YEAR_MONTHS + combo_dev
            expected_five_dedicated = (row["dedicated_cost_total"] - dedicated_dev) * calc.FIVE_YEAR_MONTHS + dedicated_dev
            assert row["five_year_combo_cost_total"] == expected_five_combo
            assert row["five_year_dedicated_cost_total"] == expected_five_dedicated
            expected_one_combo = (row["combo_cost_total"] - combo_dev) * calc.ONE_YEAR_MONTHS + combo_dev
            expected_one_dedicated = (row["dedicated_cost_total"] - dedicated_dev) * calc.ONE_YEAR_MONTHS + dedicated_dev
            assert row["one_year_combo_cost_total"] == expected_one_combo
            assert row["one_year_dedicated_cost_total"] == expected_one_dedicated

    def test_five_year_bit_total_gb_is_raw_over_eight(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            assert row["five_year_combo_bit_total_gb"] == row["five_year_combo_bit_total"] / 8.0
            assert row["five_year_dedicated_bit_total_gb"] == row["five_year_dedicated_bit_total"] / 8.0
            assert row["one_year_combo_bit_total_gb"] == row["one_year_combo_bit_total"] / 8.0
            assert row["one_year_dedicated_bit_total_gb"] == row["one_year_dedicated_bit_total"] / 8.0

    def test_five_year_cost_per_bit_is_total_over_bit(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=25)
        for row in rows:
            if row["five_year_combo_bit_total"] > 0:
                assert row["five_year_combo_cost_per_bit"] == (
                    row["five_year_combo_cost_total"] / row["five_year_combo_bit_total"]
                )
            if row["five_year_dedicated_bit_total"] > 0:
                assert row["five_year_dedicated_cost_per_bit"] == (
                    row["five_year_dedicated_cost_total"] / row["five_year_dedicated_bit_total"]
                )


class TestErWaferSaleSplit:
    """NEW model: wafer_total (ratio-swept, unchanged) never grows because of
    ER wafers -- they're carved OUT of it during each line's/recipe's own ER
    period (t <= its own t95), not produced on top of it. *_bit_total stays
    the TOTAL (sale + ER) figure with an unchanged formula; *_sale_bit_total
    is the new field netting out the ER-consumed wafers' bit contribution."""

    def test_sale_bit_total_never_exceeds_total_bit_total(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=10)
        for row in rows:
            assert row["five_year_combo_sale_bit_total"] <= row["five_year_combo_bit_total"]
            assert row["five_year_dedicated_sale_bit_total"] <= row["five_year_dedicated_bit_total"]
            assert row["one_year_combo_sale_bit_total"] <= row["one_year_combo_bit_total"]
            assert row["one_year_dedicated_sale_bit_total"] <= row["one_year_dedicated_bit_total"]

    def test_sale_bit_total_strictly_less_when_er_rate_positive_and_wafer_nonzero(self):
        params = calc.load_params(SAMPLE)
        assert params["er_wafer_combo"] > 0 and params["er_wafer_dedicated"] > 0
        rows = calc.sweep(params, ratio_step=50)
        for row in rows:
            if row["wafer_qlc_combo"] > 0 or row["wafer_tlc_combo"] > 0:
                assert row["five_year_combo_sale_bit_total"] < row["five_year_combo_bit_total"]
            if row["wafer_qlc_dedicated"] > 0 or row["wafer_tlc_dedicated"] > 0:
                assert row["five_year_dedicated_sale_bit_total"] < row["five_year_dedicated_bit_total"]

    def test_zero_er_wafer_rate_means_sale_equals_total(self):
        params = calc.load_params(SAMPLE)
        params = dict(params)
        params["er_wafer_combo"] = 0.0
        params["er_wafer_dedicated"] = 0.0
        rows = calc.sweep(params, ratio_step=50)
        for row in rows:
            assert row["five_year_combo_sale_bit_total"] == row["five_year_combo_bit_total"]
            assert row["five_year_dedicated_sale_bit_total"] == row["five_year_dedicated_bit_total"]
            assert row["one_year_combo_sale_bit_total"] == row["one_year_combo_bit_total"]
            assert row["one_year_dedicated_sale_bit_total"] == row["one_year_dedicated_bit_total"]

    def test_total_bit_formula_is_unaffected_by_er_wafer_rate(self):
        """The TOTAL bit figure must be identical regardless of the ER rate
        -- wafer_total never changes because of ER wafers, only the
        sale/ER split within it does."""
        params = calc.load_params(SAMPLE)
        rows_a = calc.sweep(params, ratio_step=50)

        bumped = dict(params)
        bumped["er_wafer_combo"] = params["er_wafer_combo"] * 10
        bumped["er_wafer_dedicated"] = params["er_wafer_dedicated"] * 10
        rows_b = calc.sweep(bumped, ratio_step=50)

        for a, b in zip(rows_a, rows_b):
            assert a["five_year_combo_bit_total"] == b["five_year_combo_bit_total"]
            assert a["five_year_dedicated_bit_total"] == b["five_year_dedicated_bit_total"]
            assert a["combo_bit_total"] == b["combo_bit_total"]
            assert a["dedicated_bit_total"] == b["dedicated_bit_total"]

    def test_er_wafer_rate_applied_in_full_independently_to_both_recipes_lines(self):
        """er_wafer_combo/er_wafer_dedicated apply in FULL (not split 50/50)
        to both of a scenario's two lines/recipes -- verify by reconstructing
        the expected five-year sale bit from calc.line_ramp_stats using the
        FULL rate on each of the two lines/recipes independently."""
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=50)
        row = next(r for r in rows if r["qlc_ratio"] == 50)

        stats_qlc = calc.line_ramp_stats(
            params["qlc_mature_yield"], params["qlc_yield_ramp_coef"], params["qlc_density"], params["qlc_gross_die"]
        )
        stats_tlc = calc.line_ramp_stats(
            params["tlc_mature_yield"], params["tlc_yield_ramp_coef"], params["tlc_density"], params["tlc_gross_die"]
        )
        er_rate = params["er_wafer_dedicated"]
        qlc_er = min(er_rate, row["wafer_qlc_dedicated"])
        tlc_er = min(er_rate, row["wafer_tlc_dedicated"])
        expected_sale = (
            row["wafer_qlc_dedicated"] * stats_qlc["bpw_5y"] - qlc_er * stats_qlc["bpw_er_5y"]
            + row["wafer_tlc_dedicated"] * stats_tlc["bpw_5y"] - tlc_er * stats_tlc["bpw_er_5y"]
        )
        assert math.isclose(row["five_year_dedicated_sale_bit_total"], expected_sale, rel_tol=1e-9)

    def test_line_ramp_stats_t95_matches_yield_ramp_t95(self):
        stats = calc.line_ramp_stats(82.0, 0.15, 48.0, 520.0)
        assert stats["t95"] == calc.yield_ramp_t95(0.15)


class TestFullBuildout:
    """full_buildout() is ratio-independent -- what each scenario would cost
    if built out to its own 100%-utilization max capacity regardless of the
    ratio actually served. combo uses combo_qlc_max_capa as its single
    representative buildout capacity (see calc.COMBO_FULL_CAPEX_ASSUMPTION).
    This calculation is entirely unchanged by the yield-ramp/cost-mode
    rework -- only its display moved from a chart to a text line (see
    render_html.py tests)."""

    def test_dedicated_sums_both_independent_lines_plus_dev_cost(self):
        params = calc.load_params(SAMPLE)
        buildout = calc.full_buildout(params)
        expected = (
            calc.capex_rate_per_wafer(params["qlc_capex_per_wafer"]) * params["qlc_max_capa"]
            + calc.capex_rate_per_wafer(params["tlc_capex_per_wafer"]) * params["tlc_max_capa"]
            + calc.dedicated_dev_cost(params)
        )
        assert buildout["dedicated"] == expected

    def test_combo_uses_qlc_max_capa_as_representative_capacity(self):
        params = calc.load_params(SAMPLE)
        buildout = calc.full_buildout(params)
        expected = (
            calc.capex_rate_per_wafer(params["combo_capex_per_wafer"]) * params["combo_qlc_max_capa"]
            + calc.combo_dev_cost(params)
        )
        assert buildout["combo"] == expected
        # Must NOT silently use combo_tlc_max_capa instead (SAMPLE deliberately
        # sets it to a different value so this would otherwise go unnoticed).
        wrong = (
            calc.capex_rate_per_wafer(params["combo_capex_per_wafer"]) * params["combo_tlc_max_capa"]
            + calc.combo_dev_cost(params)
        )
        assert buildout["combo"] != wrong

    def test_buildout_is_ratio_independent(self):
        """Sanity check that full_buildout takes no ratio argument at all --
        it is two fixed scalars, not a sweep."""
        params = calc.load_params(SAMPLE)
        buildout1 = calc.full_buildout(params)
        buildout2 = calc.full_buildout(params)
        assert buildout1 == buildout2

    def test_assumption_documents_qlc_representative_capa_choice(self):
        assert "combo_qlc_max_capa" in calc.COMBO_FULL_CAPEX_ASSUMPTION

    def test_run_includes_full_buildout_in_payload(self):
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            payload = calc.run(SAMPLE, outputs_dir, ratio_step=25)
            assert "full_buildout" in payload
            assert payload["full_buildout"]["combo"] > 0
            assert payload["full_buildout"]["dedicated"] > 0
            assert payload["full_buildout"]["combo_representative_capa_field"] == "combo_qlc_max_capa"


class TestCostMode:
    """cost_mode toggles ONLY the cost calculation -- bit production always
    uses the physical model regardless of this setting."""

    def test_cost_model_only_keys_excludes_bit_production_fields(self):
        bit_fields = {
            "qlc_density", "qlc_gross_die", "qlc_mature_yield", "qlc_yield_ramp_coef", "qlc_max_capa",
            "tlc_density", "tlc_gross_die", "tlc_mature_yield", "tlc_yield_ramp_coef", "tlc_max_capa",
            "combo_gross_die",
            "combo_qlc_density", "combo_qlc_mature_yield", "combo_qlc_yield_ramp_coef", "combo_qlc_max_capa",
            "combo_tlc_density", "combo_tlc_mature_yield", "combo_tlc_yield_ramp_coef", "combo_tlc_max_capa",
        }
        assert bit_fields.isdisjoint(calc.COST_MODEL_ONLY_KEYS)

    def test_cost_model_only_keys_covers_capex_and_dev_cost_fields(self):
        expected = {
            "qlc_capex_per_wafer", "tlc_capex_per_wafer", "combo_capex_per_wafer",
            "combo_headcount", "dedicated_headcount",
            "combo_mask_count", "dedicated_mask_count",
            "coef_cost_per_headcount", "coef_cost_per_mask",
        }
        assert set(calc.COST_MODEL_ONLY_KEYS) == expected
        assert set(calc.COST_MODEL_ONLY_KEYS) <= set(calc.REQUIRED_KEYS)

    def test_er_wafer_fields_not_in_cost_model_only_keys(self):
        """er_wafer_combo/er_wafer_dedicated feed the bit-production sale/ER
        split now, not the cost model -- they must stay enabled/required in
        BOTH cost modes, unlike the capex/dev-cost fields above."""
        assert "er_wafer_combo" not in calc.COST_MODEL_ONLY_KEYS
        assert "er_wafer_dedicated" not in calc.COST_MODEL_ONLY_KEYS

    def test_direct_cost_mode_still_uses_er_wafer_rate_for_bit_production(self):
        with tempfile.TemporaryDirectory() as td:
            params_path = Path(td) / "params.txt"
            base_text = SAMPLE.read_text(encoding="utf-8")
            base_text = re.sub(r"^cost_mode=.*$", "cost_mode=direct", base_text, flags=re.M)
            params_path.write_text(base_text, encoding="utf-8")
            outputs_dir = Path(td) / "outputs"
            payload = calc.run(params_path, outputs_dir, ratio_step=50)
            row = next(r for r in payload["sweep"] if r["qlc_ratio"] == 50)
            # ER wafers still carve a sale/ER split out of the total, even in
            # direct cost mode.
            assert row["five_year_dedicated_sale_bit_total"] < row["five_year_dedicated_bit_total"]

    def test_run_echoes_cost_mode_and_direct_cost_per_gb(self):
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            payload = calc.run(SAMPLE, outputs_dir, ratio_step=25)
            assert payload["cost_mode"] == "model"
            assert payload["direct_cost_per_gb"] == {"combo": 0.0, "dedicated": 0.0}

    def test_run_reflects_direct_cost_mode_from_params_file(self):
        with tempfile.TemporaryDirectory() as td:
            params_path = Path(td) / "params.txt"
            base_text = SAMPLE.read_text(encoding="utf-8")
            base_text = re.sub(r"^cost_mode=.*$", "cost_mode=direct", base_text, flags=re.M)
            base_text += "\ncombo_direct_cost_per_gb=12.5\ndedicated_direct_cost_per_gb=15.2\n"
            params_path.write_text(base_text, encoding="utf-8")

            outputs_dir = Path(td) / "outputs"
            payload = calc.run(params_path, outputs_dir, ratio_step=25)
            assert payload["cost_mode"] == "direct"
            assert payload["direct_cost_per_gb"] == {"combo": 12.5, "dedicated": 15.2}
            # Bit production is unaffected by cost_mode -- still computed
            # from the physical model regardless.
            assert payload["sweep"][0]["dedicated_bit_total"] >= 0


class TestCrossoverNarrative:
    """sample-1.txt is crafted so dedicated wins at low QLC ratio (high TLC
    demand -- dedicated's true TLC recipe is more bit-efficient) and combo
    wins at high QLC ratio (low TLC demand -- combo's cheaper shared capex
    dominates) -- the strategic trade-off the calculator exists to surface.
    This is judged on the MONTHLY (mature-yield) snapshot, which is
    unaffected by the yield-ramp rework."""

    def test_dedicated_wins_at_low_qlc_ratio_high_tlc_demand(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=5)
        pure_tlc_row = next(r for r in rows if r["qlc_ratio"] == 0)
        assert pure_tlc_row["dedicated_cost_per_bit"] < pure_tlc_row["combo_cost_per_bit"]

    def test_combo_wins_at_high_qlc_ratio_low_tlc_demand(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=5)
        pure_qlc_row = next(r for r in rows if r["qlc_ratio"] == 100)
        assert pure_qlc_row["combo_cost_per_bit"] < pure_qlc_row["dedicated_cost_per_bit"]

    def test_crossover_exists_between_extremes(self):
        params = calc.load_params(SAMPLE)
        rows = calc.sweep(params, ratio_step=5)
        crossover = calc.find_crossover(rows)
        assert crossover["exists"]
        assert 0 < crossover["qlc_ratio"] < 100
        # Crossover sits near QLC 60% on the mature-yield monthly snapshot --
        # renaming *_yield -> *_mature_yield (same numeric values) and adding
        # the yield-ramp/cost-mode machinery must not move this at all.
        assert 50 <= crossover["qlc_ratio"] <= 70
        assert crossover["qlc_ratio"] == 60

    def test_sample2_crossover_favors_dedicated_over_most_of_range(self):
        params = calc.load_params(SAMPLE2)
        rows = calc.sweep(params, ratio_step=5)
        crossover = calc.find_crossover(rows)
        assert crossover["exists"]
        assert crossover["qlc_ratio"] >= 70


class TestYieldRampProgressPct:
    """yield_ramp_progress_pct(ramp_coef, t) = % of mature yield reached at
    month t, independent of the mature yield value -- the formula behind the
    visualization.html "기준 시점" (yield basis) toggle's reference note."""

    def test_matches_closed_form(self):
        got = calc.yield_ramp_progress_pct(0.15, 12)
        expected = (1 - math.exp(-0.15 * 12)) * 100.0
        assert math.isclose(got, expected, rel_tol=1e-9)

    def test_zero_at_month_zero(self):
        assert calc.yield_ramp_progress_pct(0.2, 0) == 0

    def test_approaches_100_as_months_grow(self):
        assert calc.yield_ramp_progress_pct(0.2, 10_000) > 99.99

    def test_independent_of_mature_yield(self):
        """Sanity check that the helper takes no mature_yield argument at
        all -- two different mature yields must reach the SAME progress %
        at the same (ramp_coef, t)."""
        pct = calc.yield_ramp_progress_pct(0.15, 12)
        for mature in (10.0, 50.0, 99.0):
            got = calc.yield_ramp_fraction(mature, 0.15, 12) / calc.yield_fraction(mature) * 100.0
            assert math.isclose(got, pct, rel_tol=1e-9)


class TestRunEndToEnd:
    def test_writes_expected_output_files(self):
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            payload = calc.run(SAMPLE, outputs_dir, ratio_step=10)
            assert (outputs_dir / "sweep.csv").exists()
            assert (outputs_dir / "sweep.json").exists()
            assert (outputs_dir / "summary.json").exists()
            # SAMPLE sets ratio_step=5, which run() prefers over the --step
            # argument above, so the sweep is 0..100 by 5 (21 rows), not 11.
            assert len(payload["sweep"]) == 21
            assert payload["sweep"][0]["dedicated_bit_total"] > 0
            assert payload["dev_cost"]["combo"] > 0
            assert payload["dev_cost"]["dedicated"] > 0
            assert payload["is_sample"] is False
            assert "yield_ramp_curves" in payload
            assert set(payload["yield_ramp_curves"]) == {"qlc_dedicated", "qlc_combo", "tlc_dedicated", "tlc_combo"}
            assert set(payload["t95_months"]) == {"qlc", "tlc", "combo_qlc", "combo_tlc"}
            assert all(v > 0 for v in payload["t95_months"].values())
            assert "er_wafer_rate_assumption" in payload
            assert "dedicated_assumption" not in payload["dev_cost"]

    def test_sample_flag_marks_payload(self):
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            payload = calc.run(SAMPLE, outputs_dir, ratio_step=10, is_sample=True)
            assert payload["is_sample"] is True


class TestRenderHtml:
    def test_no_leftover_placeholders_and_valid_json_payload(self):
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            calc.run(SAMPLE, outputs_dir, ratio_step=10)
            html_path = outputs_dir / "visualization.html"
            render_html.render(outputs_dir / "sweep.json", html_path)

            html = html_path.read_text(encoding="utf-8")
            assert not re.findall(r"__[A-Z_]+__", html)
            # 4 ratio-swept charts (bit/cost monthly + 5yr) + 2 fixed yield-ramp
            # reference charts = 6. The old full-buildout chart was replaced by
            # a text line (fullBuildoutNote), not a 7th chart.
            assert html.count("<svg") == 6
            assert 'id="clearAll"' in html
            assert 'id="resetAll"' in html

            payload = _extract_initial_payload(html)
            assert "params" in payload
            assert "dev_cost" in payload
            assert "combo_bit_total_gb" in payload["sweep"][0]
            assert "dedicated_cost_per_gb" in payload["sweep"][0]
            assert "억GB" in html
            assert "chartCostTitle" in html

    def test_every_required_key_has_a_param_input_field(self):
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            calc.run(SAMPLE, outputs_dir, ratio_step=10)
            html_path = outputs_dir / "visualization.html"
            render_html.render(outputs_dir / "sweep.json", html_path)
            html = html_path.read_text(encoding="utf-8")
            for key in calc.REQUIRED_KEYS:
                assert f'id="param_{key}"' in html, f"missing input field for {key}"

    def test_only_the_two_shared_dev_cost_coefficients_appear(self):
        """The old step-tuning coefficient system is still gone; only the two
        flat, shared headcount/mask dev-cost conversion rates are present."""
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            calc.run(SAMPLE, outputs_dir, ratio_step=10)
            html_path = outputs_dir / "visualization.html"
            render_html.render(outputs_dir / "sweep.json", html_path)
            html = html_path.read_text(encoding="utf-8")
            assert "coefStepCost" not in html
            assert 'id="param_coef_cost_per_headcount"' in html
            assert 'id="param_coef_cost_per_mask"' in html
            for old_coef in ("coef_capex_cost", "coef_density_bit", "coef_gross_die_bit", "coef_wafer_bit", "coef_step_cost"):
                assert old_coef not in html

    def test_sample_run_shows_banner_non_sample_does_not(self):
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            calc.run(SAMPLE, outputs_dir, ratio_step=10, is_sample=True)
            html_path = outputs_dir / "visualization.html"
            render_html.render(outputs_dir / "sweep.json", html_path)
            html = html_path.read_text(encoding="utf-8")
            assert 'class="sample-banner"' in html

        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            calc.run(SAMPLE, outputs_dir, ratio_step=10, is_sample=False)
            html_path = outputs_dir / "visualization.html"
            render_html.render(outputs_dir / "sweep.json", html_path)
            html = html_path.read_text(encoding="utf-8")
            assert 'class="sample-banner"' not in html


class TestRenderHtmlBlank:
    """render_blank() / --blank is what makes the calculator usable without a
    params file at all -- real fab numbers often can't leave the fab, so the
    page must open with every field empty and still be fully functional."""

    def test_blank_payload_leaves_every_required_key_empty(self):
        payload = render_html.blank_payload()
        for key in calc.REQUIRED_KEYS:
            assert payload["params"][key] == ""

    def test_blank_payload_fabricates_no_results(self):
        payload = render_html.blank_payload()
        assert payload["sweep"] == []
        assert payload["crossover"]["exists"] is False
        assert payload["dev_cost"]["combo"] == 0
        assert payload["dev_cost"]["dedicated"] == 0
        assert payload["is_sample"] is False
        assert payload["cost_mode"] == "model"

    def test_render_blank_writes_html_with_empty_param_inputs_and_no_banner(self):
        with tempfile.TemporaryDirectory() as td:
            html_path = Path(td) / "visualization.html"
            render_html.render_blank(html_path)
            html = html_path.read_text(encoding="utf-8")
            for key in calc.REQUIRED_KEYS:
                assert f'id="param_{key}"' in html, f"missing input field for {key}"
            assert not re.findall(r"__[A-Z_]+__", html)
            assert 'class="sample-banner"' not in html


class TestChartYAxisUnitLabels:
    """The bit-production charts' y-axis must show 억GB and the cost charts'
    y-axis must show a FIXED cent/GB directly on the axis (rotated label +
    numeric ticks), not only in the chart title -- otherwise the axis looks
    like an arbitrary unit."""

    def _rendered_html(self, tmp_path):
        outputs_dir = tmp_path / "outputs"
        calc.run(SAMPLE, outputs_dir, ratio_step=10)
        html_path = outputs_dir / "visualization.html"
        render_html.render(outputs_dir / "sweep.json", html_path)
        return html_path.read_text(encoding="utf-8")

    def test_axis_unit_label_css_class_present(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert "axis-unit-label" in html

    def test_bit_chart_axis_passed_fixed_eok_gb_unit(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert (
            'id: "chartBit", series: ["combo_bit_100m_gb", "dedicated_bit_100m_gb"], unit: "억GB"' in html
        ), "bit chart must be drawn with a fixed 억GB y-axis unit"

    def test_cost_chart_axis_unit_is_fixed_cent_per_gb(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert (
            'id: "chartCost", series: ["combo_cost_per_gb_cent", "dedicated_cost_per_gb_cent"], unit: "cent/GB"' in html
        ), "cost chart's y-axis unit must be the fixed string cent/GB"
        assert "costPerGbEokwonToCent" in html
        assert 'id="exchangeRateInput"' in html

    def test_five_year_charts_present_with_fixed_units(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert 'id="chartFiveYearBit"' in html
        assert 'id="chartFiveYearCost"' in html
        assert (
            'id: "chartFiveYearBit", series: ["five_year_combo_bit_100m_gb", '
            '"five_year_dedicated_bit_100m_gb"], unit: "억GB"' in html
        )
        assert (
            'id: "chartFiveYearCost", series: ["five_year_combo_cost_per_gb_cent", '
            '"five_year_dedicated_cost_per_gb_cent"], unit: "cent/GB"' in html
        )

    def test_dev_ramp_months_input_field_no_longer_exists(self, tmp_path):
        """dev_ramp_months was removed outright -- replaced by each line's/
        recipe's own t95 (see calc.yield_ramp_t95)."""
        html = self._rendered_html(tmp_path)
        assert 'id="devRampMonthsInput"' not in html
        assert "yieldRampT95" in html

    def test_one_year_cumulative_figures_present(self, tmp_path):
        """New 1-year cumulative figures sit alongside the 5-year ones in the
        results table and the dynamic intro-stats paragraph."""
        html = self._rendered_html(tmp_path)
        assert 'id="comboOneYearBit"' in html
        assert 'id="dedOneYearBit"' in html
        assert 'id="introStats"' in html
        assert "one_year_combo_bit_total_gb" in html

    def test_full_buildout_is_text_not_a_chart(self, tmp_path):
        """The full max-capa buildout figure moved from a chart to a plain
        text line in the results panel -- calc.py's underlying computation
        (full_buildout / COMBO_FULL_CAPEX_ASSUMPTION) is unchanged, but
        there must be no chartFullBuildout SVG anymore."""
        html = self._rendered_html(tmp_path)
        assert 'id="chartFullBuildout"' not in html
        assert 'id="fullBuildoutNote"' in html
        assert "fullBuildout" in html  # the JS function computing the figure
        assert "combo_qlc_max_capa" in html

    def test_yield_ramp_charts_present_and_ratio_independent(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert 'id="chartYieldRampQlc"' in html
        assert 'id="chartYieldRampTlc"' in html
        assert "combinedRampPoints" in html
        assert "yieldRampFraction" in html
        assert "RAMP_CHART_MONTHS" in html
        # The ramp charts' x-axis is months (0..36), not the qlc_ratio slider.
        assert 'key: "month"' in html

    def test_cost_mode_toggle_present_with_disable_list(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert 'id="costModeModel"' in html
        assert 'id="costModeDirect"' in html
        assert 'id="comboDirectCostInput"' in html
        assert 'id="dedicatedDirectCostInput"' in html
        assert "updateCostModeUI" in html
        assert "COST_MODEL_ONLY_KEYS" in html
        for key in calc.COST_MODEL_ONLY_KEYS:
            assert f'"{key}"' in html

    def test_exchange_rate_input_redraws_chart(self, tmp_path):
        """Typing a new exchange rate must re-run render() (so the cost
        chart's cent/GB values update), not just sit unused."""
        html = self._rendered_html(tmp_path)
        listener_block = re.search(
            r"exchangeRateInput\.addEventListener\(\"input\", function \(\) \{(.*?)\}\);",
            html, re.S,
        )
        assert listener_block is not None
        assert "render()" in listener_block.group(1)

    def test_rotated_axis_label_and_numeric_ticks_drawn(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert "rotate(-90" in html
        assert "fmtAxisTick" in html

    def test_bit_unit_input_only_updates_labels_not_chart(self, tmp_path):
        """bit_unit never fed any chart axis -- typing a new bit_unit only
        needs to update the table's unit labels."""
        html = self._rendered_html(tmp_path)
        listener_block = re.search(
            r"bitUnitInput\.addEventListener\(\"input\", (\w+)\)",
            html, re.S,
        )
        assert listener_block is not None
        assert listener_block.group(1) == "updateUnitLabels"

    def test_currency_unit_input_also_redraws_for_buildout_text(self, tmp_path):
        """currency_unit no longer affects charts 1-4 (fixed cent/GB), but
        the full-buildout TEXT line draws its number directly in
        currency_unit with no cent conversion -- typing a new currency_unit
        must redraw so that text stays in sync."""
        html = self._rendered_html(tmp_path)
        listener_block = re.search(
            r"currencyUnitInput\.addEventListener\(\"input\", function \(\) \{(.*?)\}\);",
            html, re.S,
        )
        assert listener_block is not None
        assert "updateUnitLabels" in listener_block.group(1)
        assert "render()" in listener_block.group(1)


class TestPayloadPlainTextEditable:
    """visualization.html's initial values must be readable/editable in a
    plain text editor -- pretty-printed (not a single compact line) with
    each fab-parameter key documented inline, and re-opening the file after
    an edit must pick up the new value as the initial value."""

    def _rendered_html(self, tmp_path):
        outputs_dir = tmp_path / "outputs"
        calc.run(SAMPLE, outputs_dir, ratio_step=10)
        html_path = outputs_dir / "visualization.html"
        render_html.render(outputs_dir / "sweep.json", html_path)
        return html_path.read_text(encoding="utf-8")

    def test_payload_is_a_js_var_not_a_compact_json_script(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert 'type="application/json"' not in html
        assert "JSON.parse" not in html
        assert "var INITIAL_PAYLOAD = " in html
        assert "var data = INITIAL_PAYLOAD;" in html

    def test_payload_is_pretty_printed_multiline(self, tmp_path):
        html = self._rendered_html(tmp_path)
        match = re.search(r'var INITIAL_PAYLOAD = (\{.*?\n\});', html, re.S)
        assert match is not None
        block = match.group(1)
        assert block.count("\n") > 20, "payload should be indented across many lines, not one compact line"
        assert '    "qlc_capex_per_wafer"' in block

    def test_guidance_comment_appears_before_payload_script(self, tmp_path):
        html = self._rendered_html(tmp_path)
        script_idx = html.index('var INITIAL_PAYLOAD')
        comment_idx = html.index("<!--")
        assert comment_idx < script_idx
        guidance = html[comment_idx:script_idx]
        assert "다시 열" in guidance
        assert "초기값" in guidance

    def test_every_required_param_key_has_an_inline_comment(self, tmp_path):
        html = self._rendered_html(tmp_path)
        match = re.search(r'"params": \{(.*?)\n  \},', html, re.S)
        assert match is not None
        params_block = match.group(1)
        for key in calc.REQUIRED_KEYS:
            line = next(ln for ln in params_block.splitlines() if f'"{key}":' in ln)
            assert "//" in line, f"{key} has no inline explanatory comment"

    def test_optional_display_keys_also_commented(self, tmp_path):
        html = self._rendered_html(tmp_path)
        match = re.search(r'"params": \{(.*?)\n  \},', html, re.S)
        params_block = match.group(1)
        for key in (
            "currency_unit", "bit_unit", "ratio_step", "exchange_rate_krw_per_usd",
            "cost_mode", "combo_direct_cost_per_gb", "dedicated_direct_cost_per_gb",
        ):
            line = next(ln for ln in params_block.splitlines() if f'"{key}":' in ln)
            assert "//" in line, f"{key} has no inline explanatory comment"

    def test_editing_a_value_and_reparsing_reflects_the_edit(self, tmp_path):
        """Simulates a plain-text-editor edit: change one number in the
        payload text, then confirm the page's own extraction logic (the
        `var INITIAL_PAYLOAD = ...;` block) reflects the new value."""
        html = self._rendered_html(tmp_path)
        original = _extract_initial_payload(html)
        old_value = original["params"]["qlc_capex_per_wafer"]
        new_value = old_value + 1234

        edited_html = html.replace(
            f'"qlc_capex_per_wafer": {old_value}',
            f'"qlc_capex_per_wafer": {new_value}',
        )
        assert edited_html != html, "expected the literal value to be present and replaceable"
        edited_payload = _extract_initial_payload(edited_html)
        assert edited_payload["params"]["qlc_capex_per_wafer"] == new_value

    def test_blank_scaffold_payload_also_uses_editable_js_var(self, tmp_path):
        html_path = tmp_path / "visualization.html"
        render_html.render_blank(html_path)
        html = html_path.read_text(encoding="utf-8")
        assert 'type="application/json"' not in html
        payload = _extract_initial_payload(html)
        assert payload["params"]["qlc_capex_per_wafer"] == ""


class TestYieldBasisToggle:
    """"기준 시점" toggle: charts 1-2 (monthly Bit 생산량/Cost per GB) and the
    table's combo/dedicated Bit 생산량/Cost-per-bit cells can be switched
    between "성숙 수율 기준" (default, unchanged behavior) and "특정 개월
    기준" (a 1-60 month slider) -- everything else (5-year/1-year cumulative,
    the two yield-ramp reference charts, the verdict/crossover judgement,
    report.md) must stay wired to the base, always-mature-yield sweep."""

    def _rendered_html(self, tmp_path):
        outputs_dir = tmp_path / "outputs"
        calc.run(SAMPLE, outputs_dir, ratio_step=10)
        html_path = outputs_dir / "visualization.html"
        render_html.render(outputs_dir / "sweep.json", html_path)
        return html_path.read_text(encoding="utf-8")

    def test_basis_radio_controls_present_with_mature_as_default(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert 'id="yieldBasisMature"' in html
        assert 'id="yieldBasisMonth"' in html
        mature_tag = re.search(r'<input[^>]*id="yieldBasisMature"[^>]*>', html)
        assert mature_tag is not None
        assert "checked" in mature_tag.group(0)
        month_tag = re.search(r'<input[^>]*id="yieldBasisMonth"[^>]*>', html)
        assert month_tag is not None
        assert "checked" not in month_tag.group(0)

    def test_basis_month_slider_spans_one_to_sixty(self, tmp_path):
        html = self._rendered_html(tmp_path)
        slider_tag = re.search(r'<input[^>]*id="basisMonth"[^>]*>', html)
        assert slider_tag is not None
        assert 'min="1"' in slider_tag.group(0)
        assert 'max="60"' in slider_tag.group(0)
        assert 'type="range"' in slider_tag.group(0)

    def test_display_sweep_helpers_present(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert "computeDisplaySweep" in html
        assert "displayChartPointsFromSweep" in html
        assert "yieldFractionAtBasis" in html
        assert "rampProgressPct" in html

    def test_charts_one_and_two_read_display_sweep_not_base_sweep(self, tmp_path):
        """Charts 1-2 must be fed from monthlyChartPoints (the basis-aware
        display sweep); charts 3-4 (5-year cumulative) must stay on
        fiveYearChartPoints (the base, always-mature sweep)."""
        html = self._rendered_html(tmp_path)
        assert (
            'id: "chartBit", series: ["combo_bit_100m_gb", "dedicated_bit_100m_gb"], '
            'unit: "억GB", points: monthlyChartPoints' in html
        )
        assert (
            'id: "chartCost", series: ["combo_cost_per_gb_cent", "dedicated_cost_per_gb_cent"], '
            'unit: "cent/GB", points: monthlyChartPoints' in html
        )
        assert (
            'id: "chartFiveYearBit", series: ["five_year_combo_bit_100m_gb", '
            '"five_year_dedicated_bit_100m_gb"], unit: "억GB", points: fiveYearChartPoints' in html
        )
        assert (
            'id: "chartFiveYearCost", series: ["five_year_combo_cost_per_gb_cent", '
            '"five_year_dedicated_cost_per_gb_cent"], unit: "cent/GB", points: fiveYearChartPoints' in html
        )

    def test_table_bit_and_cost_per_bit_cells_read_display_row(self, tmp_path):
        """comboBit/dedBit and comboCostPerBit/dedCostPerBit must read from
        displayRow (basis-aware); comboCost/dedCost (Total cost, yield-
        independent) must stay on the base row."""
        html = self._rendered_html(tmp_path)
        assert '"comboBit").textContent = fmt(displayRow.combo_bit_total)' in html
        assert '"dedBit").textContent = fmt(displayRow.dedicated_bit_total)' in html
        assert '"comboCostPerBit").textContent = fmt(displayRow.combo_cost_per_bit)' in html
        assert '"dedCostPerBit").textContent = fmt(displayRow.dedicated_cost_per_bit)' in html
        assert '"comboCost").textContent = fmt(row.combo_cost_total)' in html
        assert '"dedCost").textContent = fmt(row.dedicated_cost_total)' in html

    def test_verdict_and_cumulative_and_notes_stay_on_base_row(self, tmp_path):
        """The verdict (crossover-style judgement), 1-year/5-year cumulative
        cells, and the dev-cost/ER/full-buildout notes must never reference
        displayRow -- only `row` (the base, mature-yield sweep)."""
        html = self._rendered_html(tmp_path)
        verdict_block = re.search(r"var verdict = document\.getElementById\(\"verdict\"\);(.*?)devCostNoteEl", html, re.S)
        assert verdict_block is not None
        assert "displayRow" not in verdict_block.group(1)
        assert "row.combo_cost_per_bit" in verdict_block.group(1)
        cumulative_block = re.search(r'"comboOneYearBit"\)\.textContent =(.*?)updateUnitLabels', html, re.S)
        assert cumulative_block is not None
        assert "displayRow" not in cumulative_block.group(1)

    def test_display_sweep_reuses_wafer_and_cost_total_from_base_row(self):
        """computeDisplaySweep must not recompute wafer counts or cost
        totals (yield-independent) -- only bit/cost-per-bit/cost-per-gb."""
        with tempfile.TemporaryDirectory() as td:
            outputs_dir = Path(td) / "outputs"
            calc.run(SAMPLE, outputs_dir, ratio_step=10)
            html_path = outputs_dir / "visualization.html"
            render_html.render(outputs_dir / "sweep.json", html_path)
        source = (HELPERS_DIR / "render_html.py").read_text(encoding="utf-8")
        func_match = re.search(r"function computeDisplaySweep\(params, baseRows, mode, months\) \{(.*?)\n  \}", source, re.S)
        assert func_match is not None
        body = func_match.group(1)
        assert "row.wafer_qlc_combo" in body
        assert "row.wafer_tlc_combo" in body
        assert "row.wafer_qlc_dedicated" in body
        assert "row.wafer_tlc_dedicated" in body
        assert "row.combo_cost_total" in body
        assert "row.dedicated_cost_total" in body

    def test_basis_note_element_present(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert 'id="basisYieldNote"' in html
        assert 'id="basisMonthReadout"' in html

    def test_chart_titles_updated_dynamically(self, tmp_path):
        html = self._rendered_html(tmp_path)
        assert '"chartBitTitleEl").textContent' not in html  # sanity: no typo'd id lookup
        assert "chartBitTitleEl.textContent" in html
        assert "chartCostTitleEl.textContent" in html

    def test_basis_month_slider_and_radios_only_trigger_render_not_full_recompute(self, tmp_path):
        """Moving the basis slider or flipping the radio must call render()
        directly -- not recomputeAndRender() -- since params are untouched."""
        html = self._rendered_html(tmp_path)
        slider_listener = re.search(
            r'basisMonthSlider\.addEventListener\("input", function \(\) \{(.*?)\}\);', html, re.S
        )
        assert slider_listener is not None
        assert "render()" in slider_listener.group(1)
        assert "recomputeAndRender" not in slider_listener.group(1)
