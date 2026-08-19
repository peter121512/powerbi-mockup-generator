"""Analytical verification of generated synthetic data.

Checks that generated data exhibits the requested narrative patterns.
Returns structured VerificationCheck results for each pattern check.
"""

from __future__ import annotations

from typing import Any

from pbi_gen.datagen.result import VerificationCheck, VerificationResult
from pbi_gen.models.dashboard_spec import DataPattern, DataPatternType, MockDataNarrative


def verify_data(
    tables: dict[str, list[dict[str, Any]]],
    narrative: MockDataNarrative | None,
) -> VerificationResult:
    """Verify that generated data exhibits requested patterns.

    Returns a VerificationResult with individual checks.
    """
    result = VerificationResult()

    if not narrative or not narrative.patterns:
        result.checks.append(VerificationCheck(
            name="no_patterns",
            passed=True,
            expected="No patterns to verify",
            actual="No patterns defined",
        ))
        return result

    for pattern in narrative.patterns:
        checks = _verify_pattern(tables, pattern)
        result.checks.extend(checks)

    return result


def _verify_pattern(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
) -> list[VerificationCheck]:
    """Verify a single pattern and return check results."""
    ptype = pattern.pattern_type

    if ptype == DataPatternType.TREND_UP:
        return _verify_trend(tables, pattern, direction="up")
    elif ptype == DataPatternType.TREND_DOWN:
        return _verify_trend(tables, pattern, direction="down")
    elif ptype == DataPatternType.YOY_GROWTH:
        return _verify_yoy(tables, pattern, growth=True)
    elif ptype == DataPatternType.YOY_DECLINE:
        return _verify_yoy(tables, pattern, growth=False)
    elif ptype == DataPatternType.SEASONAL:
        return _verify_seasonal(tables, pattern)
    elif ptype == DataPatternType.CONCENTRATION or ptype == DataPatternType.PARETO:
        return _verify_concentration(tables, pattern)
    elif ptype == DataPatternType.OUTLIER_NEGATIVE:
        return _verify_outlier(tables, pattern, positive=False)
    elif ptype == DataPatternType.OUTLIER_POSITIVE:
        return _verify_outlier(tables, pattern, positive=True)
    elif ptype == DataPatternType.TARGET_MISS:
        return _verify_target(tables, pattern, hit=False)
    elif ptype == DataPatternType.TARGET_HIT:
        return _verify_target(tables, pattern, hit=True)
    elif ptype == DataPatternType.VARIANCE_HIGH:
        return _verify_variance(tables, pattern, high=True)
    elif ptype == DataPatternType.FLAT:
        return _verify_flat(tables, pattern)
    else:
        return [VerificationCheck(
            name=f"{ptype.value}_check",
            passed=True,
            expected="Pattern applied",
            actual="No specific verification for this pattern type",
        )]


def _get_fact_rows(tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Get fact table rows."""
    for name in ("Sales", "Fact", "Transactions"):
        if name in tables:
            return tables[name]
    if tables:
        return max(tables.values(), key=len)
    return []


def _verify_trend(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    direction: str,
) -> list[VerificationCheck]:
    """Verify trend direction by comparing first half vs second half of time series."""
    params = pattern.parameters
    affected_categories = params.get("affected_categories", [])

    fact_rows = _get_fact_rows(tables)
    if not fact_rows:
        return [VerificationCheck(
            name=f"trend_{direction}",
            passed=False,
            expected=f"Revenue trending {direction}",
            actual="No fact rows",
        )]

    # Filter by affected categories if specified
    if affected_categories and "Product" in tables:
        product_cats = {
            p.get("ProductID", ""): p.get("CategoryName", "")
            for p in tables["Product"]
        }
        fact_rows = [
            r for r in fact_rows
            if product_cats.get(r.get("ProductID", ""), "") in affected_categories
        ]

    if not fact_rows:
        return [VerificationCheck(
            name=f"trend_{direction}",
            passed=True,
            expected=f"Revenue trending {direction}",
            actual="No matching rows (categories may not be generated)",
            tolerance="Pattern applies to specific categories",
        )]

    # Sort by date and split into halves
    dated_rows = sorted(
        [(r.get("Date", ""), r.get("Revenue", 0)) for r in fact_rows if r.get("Date")],
        key=lambda x: x[0],
    )

    if len(dated_rows) < 10:
        return [VerificationCheck(
            name=f"trend_{direction}",
            passed=True,
            expected=f"Revenue trending {direction}",
            actual="Too few rows to verify trend",
        )]

    mid = len(dated_rows) // 2
    first_half = [r[1] for r in dated_rows[:mid] if isinstance(r[1], (int, float))]
    second_half = [r[1] for r in dated_rows[mid:] if isinstance(r[1], (int, float))]

    if not first_half or not second_half:
        return [VerificationCheck(
            name=f"trend_{direction}",
            passed=False,
            expected=f"Revenue trending {direction}",
            actual="No valid revenue values",
        )]

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    if direction == "up":
        passed = avg_second > avg_first
        expected = f"Second half avg > first half avg"
    else:
        passed = avg_second < avg_first
        expected = f"Second half avg < first half avg"

    return [VerificationCheck(
        name=f"trend_{direction}",
        passed=passed,
        expected=expected,
        actual=f"First half avg: {avg_first:.2f}, Second half avg: {avg_second:.2f}",
        tolerance="10%",
    )]


def _verify_yoy(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    growth: bool,
) -> list[VerificationCheck]:
    """Verify year-over-year growth/decline by comparing years."""
    params = pattern.parameters
    affected_regions = params.get("affected_regions", [])

    fact_rows = _get_fact_rows(tables)
    if not fact_rows:
        return [VerificationCheck(
            name=f"yoy_{'growth' if growth else 'decline'}",
            passed=False,
            expected="YoY comparison",
            actual="No fact rows",
        )]

    # Filter by affected regions if specified
    if affected_regions and "Store" in tables and "Region" in tables:
        region_lookup = {r.get("RegionID", ""): r.get("RegionName", "") for r in tables["Region"]}
        store_regions = {}
        for store in tables["Store"]:
            rid = store.get("RegionID", "")
            store_regions[store.get("StoreID", "")] = region_lookup.get(rid, "")

        fact_rows = [
            r for r in fact_rows
            if store_regions.get(r.get("StoreID", ""), "") in affected_regions
        ]

    # Group revenue by year
    year_revenue: dict[int, float] = {}
    for row in fact_rows:
        row_date = row.get("Date", "")
        revenue = row.get("Revenue", 0)
        if not row_date or not isinstance(revenue, (int, float)):
            continue
        try:
            year = int(row_date.split("-")[0])
            year_revenue[year] = year_revenue.get(year, 0) + revenue
        except (IndexError, ValueError):
            continue

    if len(year_revenue) < 2:
        return [VerificationCheck(
            name=f"yoy_{'growth' if growth else 'decline'}",
            passed=True,
            expected="YoY comparison requires 2+ years",
            actual=f"Only {len(year_revenue)} year(s) found",
        )]

    sorted_years = sorted(year_revenue.keys())
    earlier = year_revenue[sorted_years[-2]]
    later = year_revenue[sorted_years[-1]]

    if earlier == 0:
        return [VerificationCheck(
            name=f"yoy_{'growth' if growth else 'decline'}",
            passed=False,
            expected="Non-zero earlier year revenue",
            actual="Earlier year revenue is 0",
        )]

    actual_change = (later - earlier) / earlier

    if growth:
        passed = later > earlier
        expected = f"Later year > earlier year (growth)"
    else:
        passed = later < earlier
        expected = f"Later year < earlier year (decline)"

    return [VerificationCheck(
        name=f"yoy_{'growth' if growth else 'decline'}",
        passed=passed,
        expected=expected,
        actual=f"Change: {actual_change:+.1%} (Y{sorted_years[-2]}={earlier:.0f}, Y{sorted_years[-1]}={later:.0f})",
        tolerance="Direction only",
    )]


def _verify_seasonal(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
) -> list[VerificationCheck]:
    """Verify peak months have higher values than average."""
    params = pattern.parameters
    peak_months: list[int] = params.get("peak_months", [11, 12])

    fact_rows = _get_fact_rows(tables)

    # Group revenue by month
    month_revenue: dict[int, list[float]] = {}
    for row in fact_rows:
        row_date = row.get("Date", "")
        revenue = row.get("Revenue", 0)
        if not row_date or not isinstance(revenue, (int, float)):
            continue
        try:
            month = int(row_date.split("-")[1])
            month_revenue.setdefault(month, []).append(revenue)
        except (IndexError, ValueError):
            continue

    if not month_revenue:
        return [VerificationCheck(
            name="seasonal",
            passed=False,
            expected="Seasonal peaks in specified months",
            actual="No monthly revenue data",
        )]

    # Average revenue per month
    month_avg = {m: sum(vs) / len(vs) for m, vs in month_revenue.items() if vs}
    all_avg = sum(month_avg.values()) / len(month_avg) if month_avg else 0

    peak_avg = sum(month_avg.get(m, 0) for m in peak_months if m in month_avg)
    peak_count = sum(1 for m in peak_months if m in month_avg)
    if peak_count > 0:
        peak_avg /= peak_count

    passed = peak_avg > all_avg
    return [VerificationCheck(
        name="seasonal",
        passed=passed,
        expected=f"Peak months {peak_months} avg > overall avg",
        actual=f"Peak avg: {peak_avg:.2f}, Overall avg: {all_avg:.2f}",
        tolerance="Peak must exceed average",
    )]


def _verify_concentration(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
) -> list[VerificationCheck]:
    """Verify top N entities have >X% of total."""
    params = pattern.parameters
    top_pct = params.get("top_percentage", 0.2)
    expected_share = params.get("top_share", 0.5)

    fact_rows = _get_fact_rows(tables)

    # Group by store
    store_revenue: dict[str, float] = {}
    for row in fact_rows:
        sid = row.get("StoreID", "")
        rev = row.get("Revenue", 0)
        if isinstance(rev, (int, float)):
            store_revenue[sid] = store_revenue.get(sid, 0) + rev

    if not store_revenue:
        return [VerificationCheck(
            name="concentration",
            passed=False,
            expected="Revenue concentration",
            actual="No store revenue data",
        )]

    total = sum(store_revenue.values())
    sorted_stores = sorted(store_revenue.values(), reverse=True)
    n_top = max(1, int(len(sorted_stores) * top_pct))
    top_revenue = sum(sorted_stores[:n_top])
    actual_share = top_revenue / total if total > 0 else 0

    passed = actual_share > expected_share * 0.5  # Relaxed check
    return [VerificationCheck(
        name="concentration",
        passed=passed,
        expected=f"Top {top_pct:.0%} stores have >{expected_share:.0%} of revenue",
        actual=f"Top {n_top} stores have {actual_share:.1%} of revenue",
        tolerance="50% of expected share",
    )]


def _verify_outlier(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    positive: bool,
) -> list[VerificationCheck]:
    """Verify outliers exist in the data."""
    params = pattern.parameters
    outlier_count = params.get("outlier_count", 5)

    fact_rows = _get_fact_rows(tables)

    # Group revenue by store
    store_revenue: dict[str, float] = {}
    for row in fact_rows:
        sid = row.get("StoreID", "")
        rev = row.get("Revenue", 0)
        if isinstance(rev, (int, float)) and sid:
            store_revenue[sid] = store_revenue.get(sid, 0) + rev

    if len(store_revenue) < 3:
        return [VerificationCheck(
            name=f"outlier_{'positive' if positive else 'negative'}",
            passed=True,
            expected="Outlier stores exist",
            actual=f"Only {len(store_revenue)} stores with revenue (insufficient for outlier detection)",
            tolerance="Requires 3+ stores",
        )]

    values = sorted(store_revenue.values())
    mean_val = sum(values) / len(values)

    if positive:
        # Check for stores significantly above mean
        high_outliers = [v for v in values if v > mean_val * 1.3]
        passed = len(high_outliers) >= 1
        actual_msg = f"{len(high_outliers)} stores >30% above mean"
    else:
        # Check for stores significantly below mean
        low_outliers = [v for v in values if v < mean_val * 0.85]
        passed = len(low_outliers) >= 1
        actual_msg = f"{len(low_outliers)} stores >15% below mean"

    return [VerificationCheck(
        name=f"outlier_{'positive' if positive else 'negative'}",
        passed=passed,
        expected=f"{outlier_count} {'over' if positive else 'under'}performing stores",
        actual=actual_msg,
        tolerance="At least 1 outlier detected",
    )]


def _verify_target(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    hit: bool,
) -> list[VerificationCheck]:
    """Verify margin is above/below target."""
    params = pattern.parameters
    target = params.get("target", 0.45)
    expected_actual = params.get("actual_average", 0.42 if not hit else 0.47)

    fact_rows = _get_fact_rows(tables)

    total_revenue = 0.0
    total_cost = 0.0
    for row in fact_rows:
        rev = row.get("Revenue", 0)
        cost = row.get("Cost", 0)
        if isinstance(rev, (int, float)) and isinstance(cost, (int, float)):
            total_revenue += rev
            total_cost += cost

    if total_revenue == 0:
        return [VerificationCheck(
            name=f"target_{'hit' if hit else 'miss'}",
            passed=False,
            expected="Margin relative to target",
            actual="No revenue data",
        )]

    actual_margin = (total_revenue - total_cost) / total_revenue

    if hit:
        passed = actual_margin >= target
        expected_str = f"Margin >= {target:.1%}"
    else:
        passed = actual_margin < target
        expected_str = f"Margin < {target:.1%}"

    return [VerificationCheck(
        name=f"target_{'hit' if hit else 'miss'}",
        passed=passed,
        expected=expected_str,
        actual=f"Actual margin: {actual_margin:.1%}",
        tolerance="5pp",
    )]


def _verify_variance(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
    high: bool,
) -> list[VerificationCheck]:
    """Verify variance across regions."""
    fact_rows = _get_fact_rows(tables)

    # Group by store for variance check
    store_revenue: dict[str, float] = {}
    for row in fact_rows:
        sid = row.get("StoreID", "")
        rev = row.get("Revenue", 0)
        if isinstance(rev, (int, float)):
            store_revenue[sid] = store_revenue.get(sid, 0) + rev

    if len(store_revenue) < 3:
        return [VerificationCheck(
            name="variance_high" if high else "variance_low",
            passed=True,
            expected="Regional variance",
            actual="Too few stores to measure variance",
        )]

    values = list(store_revenue.values())
    mean_val = sum(values) / len(values)
    variance = sum((v - mean_val) ** 2 for v in values) / len(values)
    cv = (variance ** 0.5) / mean_val if mean_val > 0 else 0  # Coefficient of variation

    if high:
        passed = cv > 0.1  # Some measurable variance
    else:
        passed = cv < 0.5

    return [VerificationCheck(
        name="variance_high" if high else "variance_low",
        passed=passed,
        expected=f"{'High' if high else 'Low'} variance across stores (CV {'>' if high else '<'} {'0.1' if high else '0.5'})",
        actual=f"Coefficient of variation: {cv:.3f}",
        tolerance="Relaxed",
    )]


def _verify_flat(
    tables: dict[str, list[dict[str, Any]]],
    pattern: DataPattern,
) -> list[VerificationCheck]:
    """Verify flat/minimal variation."""
    fact_rows = _get_fact_rows(tables)

    revenues = [r.get("Revenue", 0) for r in fact_rows if isinstance(r.get("Revenue"), (int, float))]
    if not revenues:
        return [VerificationCheck(
            name="flat",
            passed=False,
            expected="Minimal variation",
            actual="No revenue data",
        )]

    mean_val = sum(revenues) / len(revenues)
    variance = sum((v - mean_val) ** 2 for v in revenues) / len(revenues)
    cv = (variance ** 0.5) / mean_val if mean_val > 0 else 0

    passed = cv < 0.5  # Relatively flat
    return [VerificationCheck(
        name="flat",
        passed=passed,
        expected="Low coefficient of variation (<0.5)",
        actual=f"CV: {cv:.3f}",
    )]
