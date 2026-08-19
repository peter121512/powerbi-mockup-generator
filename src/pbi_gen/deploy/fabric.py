"""Deployment to Power BI Service via fabric-cicd."""

import time
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

    print("   🔑 Checking for active Azure CLI session...")
    cli_credential = _try_az_cli_credential()
    if cli_credential is not None:
        print("   ✅ Using Azure CLI credential (az login session active)")
        return cli_credential

    fallback_method = config.get("auth_method", "device_code")
    print(f"   ⚠️  No active Azure CLI session. Falling back to '{fallback_method}' auth...")
    return _get_fallback_credential(config)


def deploy_to_workspace(project_dir: Path) -> None:
    """Deploy a PBIP project to Power BI Service."""
    config = load_config()
    workspace_id = config["workspace_id"]
    credential = get_credential(config)

    print(f"   Workspace: {workspace_id}")
    print(f"   Auth: {config.get('auth_method', 'device_code')}")
    print(f"   Source: {project_dir}")

    try:
        target_workspace = FabricWorkspace(
            workspace_id=workspace_id,
            repository_directory=str(project_dir.resolve()),
            item_type_in_scope=["SemanticModel", "Report"],
            token_credential=credential,
        )
        publish_all_items(fabric_workspace_obj=target_workspace)
    except KeyError as e:
        if str(e) == "'id'":
            print("   ⚠️  Report created (first deploy quirk). Refreshing and retrying...")
            time.sleep(5)
            target_workspace = FabricWorkspace(
                workspace_id=workspace_id,
                repository_directory=str(project_dir.resolve()),
                item_type_in_scope=["SemanticModel", "Report"],
                token_credential=credential,
            )
            try:
                publish_all_items(fabric_workspace_obj=target_workspace)
            except Exception:
                pass
        else:
            raise
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            raise DeploymentError("Authentication failed. Check workspace access and authentication.") from e
        if "404" in error_msg or "not found" in error_msg.lower():
            raise DeploymentError(f"Workspace '{workspace_id}' not found or inaccessible.") from e
        if "403" in error_msg or "Forbidden" in error_msg:
            raise DeploymentError("Permission denied. Admin or Member workspace role is required.") from e
        raise DeploymentError(f"Deployment failed: {error_msg}") from e


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
    print(f"   🔄 Refreshing dataset: {dataset['name']}...")
    r = http_requests.post(
        f"{PBI_API_BASE}/groups/{workspace_id}/datasets/{dataset_id}/refreshes",
        headers=headers,
        timeout=30,
    )
    if r.status_code != 202:
        raise DeploymentError(f"Refresh trigger failed: {r.status_code} {r.text[:200]}")

    if not wait:
        print("   ✅ Refresh triggered (not waiting for completion)")
        return True

    print(f"   ⏳ Waiting for refresh to complete (timeout: {timeout}s)...")
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
                print(f"   ✅ Refresh completed ({elapsed}s)")
                return True
            if status == "Failed":
                error = refreshes[0].get("serviceExceptionJson", "Unknown error")
                print(f"   ❌ Refresh failed ({elapsed}s): {error}")
                return False
        poll_interval = min(poll_interval + 5, 20)

    print(f"   ⚠️  Refresh timeout after {timeout}s (may still be running)")
    return False
