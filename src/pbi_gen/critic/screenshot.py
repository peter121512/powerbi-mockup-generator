"""Headless screenshot capture of deployed Power BI reports.

Architecture: Uses Power BI embed token + minimal HTML host + Playwright headless browser.
Requires a service principal or user token for embed access.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from pbi_gen.critic.models import ScreenshotOutcome, ScreenshotResult


EMBED_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PBI Capture</title>
    <script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; }}
        body {{ overflow: hidden; }}
        #report {{ width: {width}px; height: {height}px; }}
    </style>
</head>
<body>
    <div id="report"></div>
    <script>
        const models = window['powerbi-client'].models;
        const config = {{
            type: 'report',
            tokenType: models.TokenType.Embed,
            accessToken: '{token}',
            embedUrl: '{embed_url}',
            id: '{report_id}',
            pageName: '{page_name}',
            settings: {{
                navContentPaneEnabled: false,
                filterPaneEnabled: false,
                layoutType: models.LayoutType.Custom,
                customLayout: {{
                    displayOption: models.DisplayOption.FitToPage,
                    pageSize: {{ type: models.PageSizeType.Custom, width: {width}, height: {height} }}
                }}
            }}
        }};

        const container = document.getElementById('report');
        const report = powerbi.embed(container, config);

        report.on('rendered', function() {{
            document.title = 'RENDERED';
        }});

        report.on('error', function(event) {{
            document.title = 'ERROR:' + JSON.stringify(event.detail);
        }});
    </script>
</body>
</html>"""


def _generate_embed_token(
    workspace_id: str,
    report_id: str,
    dataset_id: str,
    headers: dict,
) -> Optional[str]:
    """Generate a Power BI embed token for the report."""
    import requests

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken"
    body = {"accessLevel": "View", "datasetId": dataset_id}
    r = requests.post(url, headers=headers, json=body, timeout=30)
    if r.status_code == 200:
        return r.json().get("token")
    return None


def _get_embed_url(workspace_id: str, report_id: str, headers: dict) -> Optional[str]:
    """Get the embed URL for a report."""
    import requests

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}"
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code == 200:
        return r.json().get("embedUrl")
    return None


def capture_report_page(
    report_id: str,
    page_name: str,
    output_path: Path,
    *,
    workspace_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    width: int = 1280,
    height: int = 720,
    timeout_ms: int = 60000,
) -> ScreenshotResult:
    """Capture a screenshot of a deployed Power BI report page.

    Uses embed token + Playwright headless Chromium.

    Args:
        report_id: Power BI report ID.
        page_name: Page name to navigate to.
        output_path: Where to save the screenshot.
        workspace_id: Workspace ID (loads from config if None).
        dataset_id: Dataset/semantic model ID for embed token.
        width: Viewport width.
        height: Viewport height.
        timeout_ms: Max time to wait for render.

    Returns:
        ScreenshotResult with outcome and path.
    """
    start = time.time()

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
        from pbi_gen.deploy.fabric import load_config, get_credential, PBI_API_BASE

        config = load_config()
        if workspace_id is None:
            workspace_id = config["workspace_id"]

        credential = get_credential(config)
        token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
        headers = {"Authorization": f"Bearer {token}"}

        # Get embed URL
        embed_url = _get_embed_url(workspace_id, report_id, headers)
        if not embed_url:
            return ScreenshotResult(
                outcome=ScreenshotOutcome.EMBED_FAILURE,
                elapsed_seconds=time.time() - start,
                error="Could not get embed URL for report",
            )

        # Get dataset ID if not provided
        if dataset_id is None:
            import requests
            r = requests.get(
                f"{PBI_API_BASE}/groups/{workspace_id}/reports/{report_id}",
                headers=headers, timeout=30,
            )
            if r.status_code == 200:
                dataset_id = r.json().get("datasetId", "")

        # Generate embed token
        embed_token = _generate_embed_token(workspace_id, report_id, dataset_id, headers)
        if not embed_token:
            return ScreenshotResult(
                outcome=ScreenshotOutcome.AUTH_FAILURE,
                elapsed_seconds=time.time() - start,
                error="Could not generate embed token (may require Pro/PPU license or service principal)",
            )

        # Build HTML
        html_content = EMBED_HTML_TEMPLATE.format(
            width=width,
            height=height,
            token=embed_token,
            embed_url=embed_url,
            report_id=report_id,
            page_name=page_name,
        )

        # Use Playwright
        from playwright.sync_api import sync_playwright

        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_path = output_path.parent / "_embed_capture.html"
        html_path.write_text(html_content, encoding="utf-8")

        console_errors = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})

            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            page.goto(f"file:///{html_path.resolve()}")

            # Wait for title to change to RENDERED or ERROR
            try:
                page.wait_for_function(
                    "document.title.startsWith('RENDERED') || document.title.startsWith('ERROR')",
                    timeout=timeout_ms,
                )
            except Exception:
                browser.close()
                html_path.unlink(missing_ok=True)
                return ScreenshotResult(
                    outcome=ScreenshotOutcome.RENDER_TIMEOUT,
                    elapsed_seconds=time.time() - start,
                    error=f"Report did not render within {timeout_ms}ms",
                    console_errors=console_errors,
                )

            title = page.title()
            if title.startswith("ERROR"):
                browser.close()
                html_path.unlink(missing_ok=True)
                return ScreenshotResult(
                    outcome=ScreenshotOutcome.EMBED_FAILURE,
                    elapsed_seconds=time.time() - start,
                    error=f"Embed error: {title}",
                    console_errors=console_errors,
                )

            # Small delay for rendering stabilization
            page.wait_for_timeout(2000)

            # Screenshot the report container
            report_element = page.locator("#report")
            report_element.screenshot(path=str(output_path))

            browser.close()

        html_path.unlink(missing_ok=True)

        return ScreenshotResult(
            outcome=ScreenshotOutcome.SUCCESS,
            output_path=str(output_path),
            elapsed_seconds=time.time() - start,
            console_errors=console_errors,
        )

    except ImportError as e:
        return ScreenshotResult(
            outcome=ScreenshotOutcome.BROWSER_FAILURE,
            elapsed_seconds=time.time() - start,
            error=f"Missing dependency: {e}. Install playwright: pip install playwright && playwright install chromium",
        )
    except Exception as e:
        return ScreenshotResult(
            outcome=ScreenshotOutcome.BROWSER_FAILURE,
            elapsed_seconds=time.time() - start,
            error=str(e),
        )
