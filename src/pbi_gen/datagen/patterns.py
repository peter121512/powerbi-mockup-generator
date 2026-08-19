"""Narrative pattern engine for synthetic data.

Applies DataPatternType patterns to generated fact data to ensure the
mock data tells a coherent business story. All operations use a seeded
random generator for reproducibility.
"""

from __future__ import annotations

import random
from datetime import date
from typing import Any

from pbi_gen.models.dashboard_spec import DataPattern, DataPatternType, MockDataNarrative


def apply_patterns(
    tables: dict[str, list[dict[str, Any]]],
    narrative: MockDataNarrative | None,
    seed: int = 42,
) -> list[str]:
    """Apply all narrative patterns to the generated tables.

    Modifies tables in place. Returns a list of pattern descriptions applied.
    """
    if not narrative or not narrative.patterns:
        return []

    rng = random.Random(seed + 1000)  # Offset seed from generation
    applied: list[str] = []

    for pattern in narrative.patterns:
        try:
            _apply_single_pattern(tables, pattern, rng)
            applied.append(f"{pattern.pattern_type.value}: {pattern.description}")
        except Exception:
            # Pattern application is best-effort
            applied.append(f"{pattern.pattern_type.value}: SKIPPED (error)")

    return applied


def _apply_single_pattern(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
) -> None:
    """Dispatch and apply a single pattern."""
    ptype = pattern.pattern_type
    params = pattern.parameters

    if ptype == DataPatternType.TREND_UP:
        _apply_trend(tables, pattern, rng, direction=1)
    elif ptype == DataPatternType.TREND_DOWN:
        _apply_trend(tables, pattern, rng, direction=-1)
    elif ptype == DataPatternType.SEASONAL:
        _apply_seasonal(tables, pattern, rng)
    elif ptype == DataPatternType.VARIANCE_HIGH:
        _apply_variance(tables, pattern, rng, high=True)
    elif ptype == DataPatternType.VARIANCE_LOW:
        _apply_variance(tables, pattern, rng, high=False)
    elif ptype == DataPatternType.OUTLIER_NEGATIVE:
        _apply_outlier(tables, pattern, rng, positive=False)
    elif ptype == DataPatternType.OUTLIER_POSITIVE:
        _apply_outlier(tables, pattern, rng, positive=True)
    elif ptype == DataPatternType.YOY_GROWTH:
        _apply_yoy(tables, pattern, rng, growth=True)
    elif ptype == DataPatternType.YOY_DECLINE:
        _apply_yoy(tables, pattern, rng, growth=False)
    elif ptype == DataPatternType.TARGET_MISS:
        _apply_target(tables, pattern, rng, hit=False)
    elif ptype == DataPatternType.TARGET_HIT:
        _apply_target(tables, pattern, rng, hit=True)
    elif ptype == DataPatternType.CONCENTRATION:
        _apply_concentration(tables, pattern, rng)
    elif ptype == DataPatternType.PARETO:
        _apply_concentration(tables, pattern, rng)
    elif ptype == DataPatternType.RANKING_CLEAR:
        _apply_ranking(tables, pattern, rng)
    elif ptype == DataPatternType.FLAT:
        _apply_flat(tables, pattern, rng)


def _get_fact_table(tables: dict[str, list[dict[str, Any]]]) -> tuple[str, list[dict[str, Any]]]:
    """Get the main fact table (usually 'Sales')."""
    for name in ("Sales", "Fact", "Transactions"):
        if name in tables:
            return name, tables[name]
    # Fallback: largest table
    largest = max(tables.items(), key=lambda x: len(x[1]))
    return largest


def _apply_trend(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
    direction: int,
) -> None:
    """Apply TREND_UP or TREND_DOWN pattern.

    Multiplies revenue/value columns by a time-based growth/decay factor.
    If affected_categories or affected_regions are specified, only apply to matching rows.
    """
    params = pattern.parameters
    rate = params.get("growth_rate", params.get("decline_rate", 0.08))
    if direction < 0 and rate > 0:
        rate = -rate
    elif direction > 0 and rate < 0:
        rate = -rate

    affected_categories = params.get("affected_categories", [])
    affected_regions = params.get("affected_regions", [])

    fact_name, fact_rows = _get_fact_table(tables)
    if not fact_rows:
        return

    # Get date range from fact rows
    dates = sorted({row.get("Date", "") for row in fact_rows if row.get("Date")})
    if not dates:
        return

    total_days = max(1, len(dates))

    # Build category/region lookups if needed
    product_categories: dict[str, str] = {}
    store_regions: dict[str, str] = {}

    if affected_categories and "Product" in tables:
        for prod in tables["Product"]:
            product_categories[prod.get("ProductID", "")] = prod.get("CategoryName", "")

    if affected_regions and "Store" in tables and "Region" in tables:
        region_lookup = {r.get("RegionID", ""): r.get("RegionName", "") for r in tables["Region"]}
        for store in tables["Store"]:
            rid = store.get("RegionID", "")
            store_regions[store.get("StoreID", "")] = region_lookup.get(rid, "")

    for row in fact_rows:
        # Check if this row is affected
        if affected_categories:
            prod_id = row.get("ProductID", "")
            cat = product_categories.get(prod_id, "")
            if cat not in affected_categories:
                continue

        if affected_regions:
            store_id = row.get("StoreID", "")
            region = store_regions.get(store_id, "")
            if region not in affected_regions:
                continue

        # Compute time position (0 to 1)
        row_date = row.get("Date", "")
        if row_date and dates:
            try:
                idx = dates.index(row_date)
            except ValueError:
                idx = 0
            time_pos = idx / total_days
        else:
            time_pos = 0.5

        # Apply growth/decay: multiplier goes from (1 - rate/2) at start to (1 + rate/2) at end
        multiplier = 1.0 + rate * (time_pos - 0.5)

        # Add some noise
        noise = rng.uniform(0.95, 1.05)
        multiplier *= noise

        # Apply to value columns
        for col_name in ("Revenue", "Cost"):
            if col_name in row and isinstance(row[col_name], (int, float)):
                row[col_name] = round(row[col_name] * multiplier, 2)


def _apply_seasonal(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
) -> None:
    """Apply SEASONAL pattern: boost values in peak_months by peak_magnitude."""
    params = pattern.parameters
    peak_months: list[int] = params.get("peak_months", [11, 12])
    peak_magnitude: float = params.get("peak_magnitude", 0.3)

    fact_name, fact_rows = _get_fact_table(tables)

    for row in fact_rows:
        row_date = row.get("Date", "")
        if not row_date:
            continue

        try:
            month = int(row_date.split("-")[1])
        except (IndexError, ValueError):
            continue

        if month in peak_months:
            boost = 1.0 + peak_magnitude * rng.uniform(0.7, 1.3)
            for col_name in ("Revenue", "Cost"):
                if col_name in row and isinstance(row[col_name], (int, float)):
                    row[col_name] = round(row[col_name] * boost, 2)


def _apply_variance(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
    high: bool,
) -> None:
    """Apply VARIANCE_HIGH/VARIANCE_LOW: adjust spread across regions/categories."""
    params = pattern.parameters
    magnitude: float = params.get("variance_magnitude", 0.4 if high else 0.1)

    fact_name, fact_rows = _get_fact_table(tables)

    # Determine grouping (by Store -> Region)
    if "Store" in tables and "Region" in tables:
        region_lookup = {r.get("RegionID", ""): r.get("RegionName", "") for r in tables["Region"]}
        store_regions: dict[str, str] = {}
        for store in tables["Store"]:
            rid = store.get("RegionID", "")
            store_regions[store.get("StoreID", "")] = region_lookup.get(rid, "")

        # Assign region multipliers
        regions = list(set(store_regions.values()))
        regions.sort()
        region_multipliers: dict[str, float] = {}
        n = len(regions)
        for i, region in enumerate(regions):
            # Spread multipliers around 1.0
            offset = (i / max(1, n - 1) - 0.5) * 2 * magnitude
            region_multipliers[region] = 1.0 + offset

        for row in fact_rows:
            store_id = row.get("StoreID", "")
            region = store_regions.get(store_id, "")
            mult = region_multipliers.get(region, 1.0)
            noise = rng.uniform(0.92, 1.08)
            for col_name in ("Revenue", "Cost"):
                if col_name in row and isinstance(row[col_name], (int, float)):
                    row[col_name] = round(row[col_name] * mult * noise, 2)


def _apply_outlier(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
    positive: bool,
) -> None:
    """Apply OUTLIER_NEGATIVE/POSITIVE: mark specific stores for under/over-performance."""
    params = pattern.parameters
    outlier_count: int = params.get("outlier_count", 5)
    outlier_magnitude: float = params.get("outlier_magnitude", -0.25 if not positive else 0.25)

    fact_name, fact_rows = _get_fact_table(tables)

    # Select outlier stores
    if "Store" in tables:
        store_ids = [s.get("StoreID", "") for s in tables["Store"]]
        if len(store_ids) > outlier_count:
            outlier_stores = set(rng.sample(store_ids, outlier_count))
        else:
            outlier_stores = set(store_ids[:outlier_count])

        for row in fact_rows:
            if row.get("StoreID", "") in outlier_stores:
                multiplier = 1.0 + outlier_magnitude
                noise = rng.uniform(0.9, 1.1)
                for col_name in ("Revenue",):
                    if col_name in row and isinstance(row[col_name], (int, float)):
                        row[col_name] = round(row[col_name] * multiplier * noise, 2)
                # Cost stays relatively fixed (makes margin worse for negative outliers)


def _apply_yoy(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
    growth: bool,
) -> None:
    """Apply YOY_GROWTH/YOY_DECLINE: ensure year-over-year comparison shows correct direction.

    If affected_regions is specified, only apply to matching rows.
    """
    params = pattern.parameters
    rate = params.get("growth_rate" if growth else "decline_rate", 0.08 if growth else -0.07)
    affected_regions = params.get("affected_regions", [])

    fact_name, fact_rows = _get_fact_table(tables)

    # Build store->region lookup if needed
    store_regions: dict[str, str] = {}
    if affected_regions and "Store" in tables and "Region" in tables:
        region_lookup = {r.get("RegionID", ""): r.get("RegionName", "") for r in tables["Region"]}
        for store in tables["Store"]:
            rid = store.get("RegionID", "")
            store_regions[store.get("StoreID", "")] = region_lookup.get(rid, "")

    # Find the year boundary
    years: set[int] = set()
    for row in fact_rows:
        row_date = row.get("Date", "")
        if row_date:
            try:
                y = int(row_date.split("-")[0])
                years.add(y)
            except (IndexError, ValueError):
                pass

    if len(years) < 2:
        return

    sorted_years = sorted(years)
    earlier_years = set(sorted_years[:-1])

    # Reduce earlier year values so later year shows growth (or vice versa)
    for row in fact_rows:
        if affected_regions:
            store_id = row.get("StoreID", "")
            region = store_regions.get(store_id, "")
            if region not in affected_regions:
                continue

        row_date = row.get("Date", "")
        if not row_date:
            continue

        try:
            y = int(row_date.split("-")[0])
        except (IndexError, ValueError):
            continue

        if y in earlier_years:
            # For growth: reduce earlier years so later appears bigger
            # For decline: boost earlier years so later appears smaller
            if growth:
                adjustment = 1.0 / (1.0 + abs(rate))
            else:
                adjustment = 1.0 / (1.0 + rate)  # rate is negative for decline
            noise = rng.uniform(0.95, 1.05)
            for col_name in ("Revenue", "Cost"):
                if col_name in row and isinstance(row[col_name], (int, float)):
                    row[col_name] = round(row[col_name] * adjustment * noise, 2)


def _apply_target(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
    hit: bool,
) -> None:
    """Apply TARGET_MISS/TARGET_HIT: adjust margins to be below/above target.

    For target_miss: ensures Cost/Revenue ratio gives margin below target.
    For target_hit: ensures Cost/Revenue ratio gives margin above target.
    """
    params = pattern.parameters
    target: float = params.get("target", 0.45)
    actual_average: float = params.get("actual_average", 0.42 if not hit else 0.47)

    fact_name, fact_rows = _get_fact_table(tables)

    # Adjust cost to achieve desired margin
    # Margin = (Revenue - Cost) / Revenue
    # => Cost = Revenue * (1 - margin)
    desired_margin = actual_average

    for row in fact_rows:
        revenue = row.get("Revenue")
        if revenue and isinstance(revenue, (int, float)) and revenue > 0:
            # Add noise to margin per-row
            row_margin = desired_margin + rng.uniform(-0.08, 0.08)
            row_margin = max(0.1, min(0.7, row_margin))  # Clamp
            new_cost = revenue * (1.0 - row_margin)
            row["Cost"] = round(max(0.01, new_cost), 2)


def _apply_concentration(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
) -> None:
    """Apply CONCENTRATION/PARETO: skew distribution so top entities dominate."""
    params = pattern.parameters
    top_share: float = params.get("top_share", 0.7)  # Top 20% get 70% of revenue
    top_pct: float = params.get("top_percentage", 0.2)

    fact_name, fact_rows = _get_fact_table(tables)

    if "Store" not in tables:
        return

    store_ids = sorted({s.get("StoreID", "") for s in tables["Store"]})
    n_top = max(1, int(len(store_ids) * top_pct))
    top_stores = set(store_ids[:n_top])

    # Boost top stores, reduce others
    boost_factor = top_share / top_pct  # e.g. 0.7/0.2 = 3.5
    reduce_factor = (1.0 - top_share) / (1.0 - top_pct)  # e.g. 0.3/0.8 = 0.375

    for row in fact_rows:
        store_id = row.get("StoreID", "")
        if store_id in top_stores:
            mult = boost_factor * rng.uniform(0.85, 1.15)
        else:
            mult = reduce_factor * rng.uniform(0.85, 1.15)

        for col_name in ("Revenue", "Cost"):
            if col_name in row and isinstance(row[col_name], (int, float)):
                row[col_name] = round(row[col_name] * mult, 2)


def _apply_ranking(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
) -> None:
    """Apply RANKING_CLEAR: ensure clear ordering in values by group."""
    # Similar to concentration but ensures distinct ranking tiers
    fact_name, fact_rows = _get_fact_table(tables)

    if "Store" not in tables:
        return

    store_ids = sorted({s.get("StoreID", "") for s in tables["Store"]})
    n = len(store_ids)
    # Assign rank multipliers: top store gets highest, bottom gets lowest
    rank_mults = {sid: 1.0 + 0.5 * (1.0 - i / max(1, n - 1)) for i, sid in enumerate(store_ids)}

    for row in fact_rows:
        store_id = row.get("StoreID", "")
        mult = rank_mults.get(store_id, 1.0)
        noise = rng.uniform(0.95, 1.05)
        for col_name in ("Revenue",):
            if col_name in row and isinstance(row[col_name], (int, float)):
                row[col_name] = round(row[col_name] * mult * noise, 2)


def _apply_flat(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    rng: random.Random,
) -> None:
    """Apply FLAT: minimal variation - compress values toward mean."""
    fact_name, fact_rows = _get_fact_table(tables)

    if not fact_rows:
        return

    # Compute mean revenue
    revenues = [r.get("Revenue", 0) for r in fact_rows if isinstance(r.get("Revenue"), (int, float))]
    if not revenues:
        return

    mean_rev = sum(revenues) / len(revenues)

    for row in fact_rows:
        rev = row.get("Revenue")
        if isinstance(rev, (int, float)):
            # Move 80% toward mean
            new_rev = mean_rev + (rev - mean_rev) * 0.2
            noise = rng.uniform(0.98, 1.02)
            row["Revenue"] = round(new_rev * noise, 2)
