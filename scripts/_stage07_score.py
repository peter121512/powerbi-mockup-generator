"""Stage 07: Re-render, deploy, capture all 4 pages, and score."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.models.dashboard_spec import DashboardSpec
from pbi_gen.deploy.staging import generate_inline_m_from_db
from pbi_gen.renderer import render_powerbi_project
from pbi_gen.deploy.fabric import deploy_report_direct
from pbi_gen.critic.screenshot import capture_report_page
from pbi_gen.critic.critic import critique_visuals

spec = DashboardSpec.model_validate(json.loads(
    Path("docs/stages/02a-live-designer-test/LIVE_OUTPUT.json").read_text(encoding="utf-8")
))
db_path = Path("build/live_data/retail_dashboard.db")
partition_sources = {
    t.name: m for t in spec.tables
    if (m := generate_inline_m_from_db(t.name, db_path, table_spec=t))
}

render_result = render_powerbi_project(spec=spec, output_dir=Path("build/deploy"), partition_sources=partition_sources)
print(f"Render: {render_result.outcome.value}")
report_id = deploy_report_direct(Path(render_result.output_path))
print(f"Deploy: {report_id}")

out_dir = Path("docs/stages/07-enterprise-visual-baseline")
pages = [
    ("Executive Overview", "executive-baseline-after.png"),
    ("Regional Analysis", "regional-baseline-after.png"),
    ("Category Analysis", "category-baseline-after.png"),
    ("Risk Analysis", "risk-baseline-after.png"),
]
for pn, fn in pages:
    r = capture_report_page(report_id, pn, out_dir / fn)
    print(f"  {pn}: {r.outcome.value}")

# Critic
exec_page = next(p for p in spec.pages if "executive" in p.title.lower())
critique = critique_visuals(
    requirement="Executive retail performance dashboard for CEO/CFO",
    spec=spec,
    page_id=exec_page.id,
    reference_path=Path("docs/stages/06-visual-reference-critic-loop/reference-executive-overview.png"),
    actual_path=out_dir / "executive-baseline-after.png",
)

s06 = json.loads(Path("docs/stages/06-visual-reference-critic-loop/critique-after.json").read_text())["scores"]
print(f"\nOverall: {s06['overall']} -> {critique.scores.overall} (delta: {critique.scores.overall - s06['overall']:+.1f})")
print(f"Filter:  {s06['filter_placement']} -> {critique.scores.filter_placement}")
print(f"White:   {s06['whitespace']} -> {critique.scores.whitespace}")
print(f"KPI:     {s06['kpi_prominence']} -> {critique.scores.kpi_prominence}")
print(f"Align:   {s06['alignment_grid']} -> {critique.scores.alignment_grid}")
print(f"Typo:    {s06['typography_readability']} -> {critique.scores.typography_readability}")
print(f"Polish:  {s06['polish_premium']} -> {critique.scores.polish_premium}")

Path("docs/stages/07-enterprise-visual-baseline/critique-stage07.json").write_text(
    json.dumps(critique.model_dump(), indent=2), encoding="utf-8"
)
print(f"\nSummary: {critique.summary[:150]}")
