"""Deployment to Power BI Service via fabric-cicd + Fabric REST API."""

import base64
import json
import time
import uuid
import yaml
from pathlib import Path

import requests as http_requests
from azure.identity import (
    ClientSecretCredential,
    DeviceCodeCredential,
    AzureCliCredential,
    InteractiveBrowserCredential,
    TokenCachePersistenceOptions,
)
from fabric_cicd import FabricWorkspace, publish_all_items


CONFIG_PATH = Path.home() / ".pbi_gen" / "config.yaml"
TOKEN_CACHE_DIR = Path.home() / ".pbi_gen"
PBI_API_BASE = "https://api.powerbi.com/v1.0/myorg"
FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


class DeploymentError(Exception):
    """Raised when deployment fails."""
    pass


def load_config() -> dict:
    """Load deployment config from ~/.pbi_gen/config.yaml."""
    if not CONFIG_PATH.exists():
        raise DeploymentError(
            f"No config found at {CONFIG_PATH}\n"
            f"Create it with:\n"
            f"  mkdir -p ~/.pbi_gen\n"
            f"  cp config.example.yaml ~/.pbi_gen/config.yaml\n"
            f"Then fill in your workspace_id.\n\n"
            f"To get your workspace ID:\n"
            f"  1. Go to app.powerbi.com\n"
            f"  2. Open your workspace\n"
            f"  3. Copy the ID from the URL: /groups/<workspace_id>"
        )

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    if not config.get("workspace_id"):
        raise DeploymentError(
            f"workspace_id is empty in {CONFIG_PATH}\n"
            f"Set it to your Power BI workspace ID from the URL."
        )

    return config


def _try_az_cli_credential():
    """Attempt to use Azure CLI credential by requesting a token."""
    try:
        credential = AzureCliCredential()
        credential.get_token("https://analysis.windows.net/powerbi/api/.default")
        return credential
    except Exception:
        return None


def _get_fallback_credential(config: dict):
    """Get credential using the user's configured auth_method (fallback)."""
    auth_method = config.get("auth_method", "device_code")
    tenant_id = config.get("tenant_id") or None

    cache_options = TokenCachePersistenceOptions(
        name="pbi_gen_token_cache",
        allow_unencrypted_storage=True,
    )

    if auth_method == "az_cli":
        return AzureCliCredential()
    if auth_method == "browser":
        return InteractiveBrowserCredential(
            tenant_id=tenant_id,
            cache_persistence_options=cache_options,
        )
    if auth_method == "device_code":
        return DeviceCodeCredential(
            tenant_id=tenant_id,
            cache_persistence_options=cache_options,
        )
    raise DeploymentError(
        f"Unknown auth_method '{auth_method}' in config.\n"
        f"Valid options: device_code, az_cli, browser"
    )


def get_credential(config: dict):
    """Get the appropriate TokenCredential."""
    auth_method = config.get("auth_method", "device_code")

    if auth_method == "service_principal":
        tenant_id = config.get("tenant_id")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        if not all([tenant_id, client_id, client_secret]):
            raise DeploymentError(
                "auth_method is 'service_principal' but credentials are incomplete.\n"
                "Set tenant_id, client_id, and client_secret in ~/.pbi_gen/config.yaml"
            )
        print("   🔑 Authenticating with service principal...")
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    if auth_method == "az_cli":
        return AzureCliCredential()

    print("   [*] Checking for active Azure CLI session...")
    cli_credential = _try_az_cli_credential()
    if cli_credential is not None:
        print("   [OK] Using Azure CLI credential (az login session active)")
        return cli_credential

    fallback_method = config.get("auth_method", "device_code")
    print(f"   [WARN] No active Azure CLI session. Falling back to '{fallback_method}' auth...")
    return _get_fallback_credential(config)


def refresh_dataset(dataset_name: str | None = None, wait: bool = True, timeout: int = 300) -> bool:
    """Trigger a dataset refresh after deployment so inline data gets loaded."""
    config = load_config()
    workspace_id = config["workspace_id"]
    credential = get_credential(config)
    token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
    headers = {"Authorization": f"Bearer {token}"}

    r = http_requests.get(
        f"{PBI_API_BASE}/groups/{workspace_id}/datasets", headers=headers, timeout=30
    )
    r.raise_for_status()
    datasets = r.json().get("value", [])
    if not datasets:
        raise DeploymentError("No datasets found in workspace.")

    if dataset_name:
        dataset = next((d for d in datasets if d["name"].lower() == dataset_name.lower()), None)
        if not dataset:
            available = [d["name"] for d in datasets]
            raise DeploymentError(f"Dataset '{dataset_name}' not found. Available: {available}")
    else:
        dataset = datasets[0]

    dataset_id = dataset["id"]
    print(f"   [*] Refreshing dataset: {dataset['name']}...")
    r = http_requests.post(
        f"{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/refreshes",
        headers=headers,
        timeout=30,
    )
    if r.status_code != 202:
        raise DeploymentError(f"Refresh trigger failed: {r.status_code} {r.text[:200]}")

    if not wait:
        print("   [OK] Refresh triggered (not waiting for completion)")
        return True

    print(f"   [..] Waiting for refresh to complete (timeout: {timeout}s)...")
    start = time.time()
    poll_interval = 5
    while time.time() - start < timeout:
        time.sleep(poll_interval)
        r = http_requests.get(
            f"{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/refreshes?$top=1",
            headers=headers,
            timeout=30,
        )
        refreshes = r.json().get("value", [])
        if refreshes:
            status = refreshes[0].get("status", "Unknown")
            elapsed = int(time.time() - start)
            if status == "Completed":
                print(f"   [OK] Refresh completed ({elapsed}s)")
                return True
            if status == "Failed":
                error = refreshes[0].get("serviceExceptionJson", "Unknown error")
                print(f"   [FAIL] Refresh failed ({elapsed}s): {error}")
                return False
        poll_interval = min(poll_interval + 5, 20)

    print(f"   [WARN] Refresh timeout after {timeout}s (may still be running)")
    return False



# ─────────────────────────────────────────────────────────────────────────────
# Direct Fabric API report deployment (bypasses fabric-cicd for reports)
# ─────────────────────────────────────────────────────────────────────────────


def _collect_report_parts(report_dir: Path, semantic_model_id: str, workspace_name: str) -> list[dict]:
    """Collect all report files as base64-encoded parts for the Fabric API.

    The key difference from fabric-cicd: we use byConnection with the explicit
    semantic model ID instead of byPath. This produces reports that actually
    render in the Fabric web UI.
    """
    parts = []
    report_def_dir = report_dir / "definition"

    # .platform
    platform_path = report_dir / ".platform"
    if platform_path.exists():
        platform = json.loads(platform_path.read_text(encoding="utf-8"))
        parts.append(_make_part(".platform", platform))

    # definition.pbir — override with byConnection
    display_name = json.loads(platform_path.read_text(encoding="utf-8"))["metadata"]["displayName"] if platform_path.exists() else report_dir.name.replace(".Report", "")
    pbir = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {
            "byConnection": {
                "connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_name};initial catalog={display_name};integrated security=ClaimsToken;semanticmodelid={semantic_model_id}"
            }
        },
    }
    parts.append(_make_part("definition.pbir", pbir))

    # Walk definition/ folder for all JSON files
    if report_def_dir.exists():
        for file_path in sorted(report_def_dir.rglob("*.json")):
            rel_path = file_path.relative_to(report_dir).as_posix()
            content = file_path.read_bytes()
            parts.append({
                "path": rel_path,
                "payload": base64.b64encode(content).decode("ascii"),
                "payloadType": "InlineBase64",
            })

    # StaticResources
    static_dir = report_dir / "StaticResources"
    if static_dir.exists():
        for file_path in sorted(static_dir.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(report_dir).as_posix()
                content = file_path.read_bytes()
                parts.append({
                    "path": rel_path,
                    "payload": base64.b64encode(content).decode("ascii"),
                    "payloadType": "InlineBase64",
                })

    return parts


def _make_part(path: str, obj: dict) -> dict:
    """Create a base64-encoded part from a dict."""
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return {
        "path": path,
        "payload": base64.b64encode(payload).decode("ascii"),
        "payloadType": "InlineBase64",
    }


def _wait_for_operation(op_id: str, location: str, headers: dict, timeout: int = 120) -> dict:
    """Poll a long-running Fabric operation until completion."""
    start = time.time()
    poll_url = location or f"{FABRIC_API_BASE}/operations/{op_id}"
    while time.time() - start < timeout:
        time.sleep(3)
        r = http_requests.get(poll_url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "")
            if status == "Succeeded":
                return data
            if status == "Failed":
                error = data.get("error", {})
                raise DeploymentError(f"Operation failed: {error.get('message', str(error))}")
    raise DeploymentError(f"Operation timed out after {timeout}s")


def _find_item_by_name(workspace_id: str, item_type: str, name: str, headers: dict) -> str | None:
    """Find an item ID by type and name in the workspace."""
    r = http_requests.get(
        f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items?type={item_type}",
        headers=headers, timeout=30,
    )
    if r.status_code == 200:
        for item in r.json().get("value", []):
            if item["displayName"].lower() == name.lower():
                return item["id"]
    return None


def deploy_report_direct(
    project_dir: Path,
    *,
    semantic_model_id: str | None = None,
) -> str:
    """Deploy a report using the Fabric REST API directly.

    This bypasses fabric-cicd for the report item, which fixes the rendering
    issue where fabric-cicd-deployed reports show endless spinners.

    Args:
        project_dir: Root of the PBIP project (contains .pbip file).
        semantic_model_id: ID of the deployed semantic model. If None,
            looks it up by name in the workspace.

    Returns:
        The report item ID.
    """
    config = load_config()
    workspace_id = config["workspace_id"]
    workspace_name = config.get("workspace_name", "pbi")
    credential = get_credential(config)
    token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Find the report directory
    report_dirs = list(project_dir.glob("*.Report"))
    if not report_dirs:
        raise DeploymentError(f"No .Report directory found in {project_dir}")
    report_dir = report_dirs[0]

    # Get display name from .platform
    platform_path = report_dir / ".platform"
    if platform_path.exists():
        platform = json.loads(platform_path.read_text(encoding="utf-8"))
        display_name = platform["metadata"]["displayName"]
    else:
        display_name = report_dir.name.replace(".Report", "")

    # Get semantic model ID if not provided
    if semantic_model_id is None:
        semantic_model_id = _find_item_by_name(
            workspace_id, "SemanticModel", display_name, headers
        )
        if not semantic_model_id:
            raise DeploymentError(
                f"Semantic model '{display_name}' not found in workspace. "
                f"Deploy the semantic model first."
            )

    print(f"   [*] Deploying report '{display_name}' via Fabric API...")
    print(f"       Semantic model: {semantic_model_id}")

    # Collect parts
    parts = _collect_report_parts(report_dir, semantic_model_id, workspace_name)
    print(f"       Parts: {len(parts)}")

    # Check if report already exists
    existing_id = _find_item_by_name(workspace_id, "Report", display_name, headers)

    if existing_id:
        # Update existing report definition
        print(f"       Updating existing report: {existing_id}")
        url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items/{existing_id}/updateDefinition"
        body = {"definition": {"parts": parts}}
        r = http_requests.post(url, headers=headers, json=body, timeout=60)
    else:
        # Create new report
        print(f"       Creating new report...")
        url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items"
        body = {
            "displayName": display_name,
            "type": "Report",
            "definition": {"parts": parts},
        }
        r = http_requests.post(url, headers=headers, json=body, timeout=60)

    if r.status_code == 200:
        print(f"   [OK] Report deployed: {existing_id or r.json().get('id', '?')}")
        return existing_id or r.json().get("id", "")
    elif r.status_code in (201, 202):
        op_id = r.headers.get("x-ms-operation-id", "")
        location = r.headers.get("Location", "")
        if op_id or location:
            _wait_for_operation(op_id, location, headers)
        report_id = existing_id or ""
        if not report_id and r.status_code == 201:
            report_id = r.json().get("id", "")
        if not report_id:
            # Look up newly created report
            report_id = _find_item_by_name(workspace_id, "Report", display_name, headers) or ""
        print(f"   [OK] Report deployed: {report_id}")
        return report_id
    else:
        raise DeploymentError(f"Report deployment failed: {r.status_code} {r.text[:500]}")


def deploy_to_workspace(project_dir: Path) -> None:
    """Deploy a PBIP project to Power BI Service.

    Uses fabric-cicd for the semantic model, then the direct Fabric API
    for the report (to avoid the rendering bug with fabric-cicd reports).
    """
    config = load_config()
    workspace_id = config["workspace_id"]
    credential = get_credential(config)

    print(f"   Workspace: {workspace_id}")
    print(f"   Auth: {config.get('auth_method', 'device_code')}")
    print(f"   Source: {project_dir}")

    # Step 1: Deploy semantic model via fabric-cicd
    print("   [1/2] Deploying semantic model via fabric-cicd...")
    try:
        target_workspace = FabricWorkspace(
            workspace_id=workspace_id,
            repository_directory=str(project_dir.resolve()),
            item_type_in_scope=["SemanticModel"],
            token_credential=credential,
        )
        publish_all_items(fabric_workspace_obj=target_workspace)
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            raise DeploymentError("Authentication failed.") from e
        if "404" in error_msg or "not found" in error_msg.lower():
            raise DeploymentError(f"Workspace '{workspace_id}' not found.") from e
        if "403" in error_msg or "Forbidden" in error_msg:
            raise DeploymentError("Permission denied.") from e
        raise DeploymentError(f"Semantic model deployment failed: {error_msg}") from e

    # Step 2: Deploy report via direct Fabric API
    print("   [2/2] Deploying report via Fabric REST API...")
    deploy_report_direct(project_dir)
