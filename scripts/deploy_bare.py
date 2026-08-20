"""Deploy an absolutely bare-minimum report: just a page, no visuals, no theme."""
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbi_gen.deploy.fabric import deploy_to_workspace


def main():
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "build" / "diag_bare" / "BareMinimal"
    output_dir.mkdir(parents=True, exist_ok=True)

    project_name = "BareMinimal"

    # .pbip
    pbip = {
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{project_name}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }
    _write(output_dir / f"{project_name}.pbip", pbip)
    _write_text(output_dir / ".gitignore", "*.pbicache\n.pbi/\n")

    # Semantic Model
    sm_root = output_dir / f"{project_name}.SemanticModel"
    sm_def = sm_root / "definition"

    _write(sm_root / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": project_name},
        "config": {"version": "2.0", "logicalId": str(uuid4())},
    })
    _write(sm_root / "definition.pbism", {"version": "4.0", "settings": {}})
    _write_text(sm_def / "model.tmdl", 'model Model\n\tculture: en-GB\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n')
    _write_text(sm_def / "tables" / "Fact.tmdl",
        'table Fact\n\tlineageTag: ' + str(uuid4()) + '\n\n'
        '\tcolumn ID\n\t\tdataType: int64\n\t\tlineageTag: ' + str(uuid4()) + '\n\t\tsummarizeBy: none\n\t\tsourceColumn: ID\n\n'
        '\tcolumn Value\n\t\tdataType: double\n\t\tlineageTag: ' + str(uuid4()) + '\n\t\tsummarizeBy: sum\n\t\tsourceColumn: Value\n\n'
        '\tmeasure Total = SUM(Fact[Value])\n\t\tlineageTag: ' + str(uuid4()) + '\n\t\tformatString: #,0\n\n'
        '\tpartition Fact = m\n\t\tmode: import\n\t\tsource =\n\t\t\tlet\n\t\t\t\tSource = #table({"ID","Value"}, {{1,100},{2,200},{3,300}}),\n\t\t\t\tTyped = Table.TransformColumnTypes(Source, {{"ID", Int64.Type}, {"Value", type number}})\n\t\t\tin\n\t\t\t\tTyped\n'
    )

    # Report
    rpt_root = output_dir / f"{project_name}.Report"
    rpt_def = rpt_root / "definition"

    _write(rpt_root / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": project_name},
        "config": {"version": "2.0", "logicalId": str(uuid4())},
    })

    # definition.pbir
    _write(rpt_root / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{project_name}.SemanticModel"}},
    })

    # version.json
    _write(rpt_def / "version.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })

    # report.json - matching known-working schema versions
    _write(rpt_def / "report.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU06",
                "reportVersionAtImport": "5.61",
                "type": "SharedResources",
            }
        },
        "layoutOptimization": "None",
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": "CY24SU06",
                        "type": "BaseTheme",
                        "path": "BaseThemes/CY24SU06.json",
                    }
                ],
            },
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultFilterActionIsDataFilter": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "allowInlineExploration": True,
            "useEnhancedTooltips": True,
        },
    })

    # pages.json
    _write(rpt_def / "pages" / "pages.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": ["page1"],
        "activePageName": "page1",
    })

    # Single page - NO visuals at all
    _write(rpt_def / "pages" / "page1" / "page.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
        "name": "page1",
        "displayName": "Page 1",
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
    })

    print(f"Generated: {output_dir}")
    print("Deploying...")
    try:
        deploy_to_workspace(output_dir)
        print("Deployed!")
    except Exception as e:
        print(f"Deploy failed: {e}")


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def _write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
