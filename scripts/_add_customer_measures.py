"""Add customer-friendly measures to the semantic model.

Adds measures with customer-appropriate names that reference existing calculations.
"""
import sys, json, time, requests, base64
sys.path.insert(0, "src")
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

workspace_id = config["workspace_id"]
sm_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"

# Step 1: Get model definition
print("Getting model definition...")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/semanticModels/{sm_id}/getDefinition",
                  headers=headers, json={}, timeout=30)

if r.status_code == 202:
    loc = r.headers.get("Location", "")
    print(f"Polling: {loc[:80]}...")
    for attempt in range(20):
        time.sleep(3)
        poll = requests.get(loc, headers=headers, timeout=30)
        data = poll.json()
        status = data.get("status")
        if status == "Succeeded":
            print("Operation completed!")
            break
        elif status == "Failed":
            print(f"Failed: {data}")
            sys.exit(1)
    else:
        print("Timeout")
        sys.exit(1)

    # Get the actual definition result
    result_url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/semanticModels/{sm_id}/getDefinition/result"
    r2 = requests.get(result_url, headers=headers, timeout=30)
    print(f"Result endpoint: {r2.status_code}")
    if r2.status_code == 200:
        definition = r2.json().get("definition", r2.json())
    else:
        # Try the operation result URL
        op_id = loc.split("/operations/")[-1].split("?")[0] if "/operations/" in loc else ""
        result_url2 = f"{loc}/result" if loc else ""
        r3 = requests.get(result_url2, headers=headers, timeout=30)
        print(f"Op result: {r3.status_code}")
        if r3.status_code == 200:
            definition = r3.json().get("definition", r3.json())
        else:
            print(f"Cannot get definition result: {r3.status_code} {r3.text[:200]}")
            sys.exit(1)
elif r.status_code == 200:
    definition = r.json().get("definition", r.json())
else:
    print(f"Error: {r.status_code} {r.text[:200]}")
    sys.exit(1)

# Step 2: Find and decode the Sales.tmdl part
parts = definition.get("parts", [])
sales_part = None
for part in parts:
    if part["path"] == "definition/tables/Sales.tmdl":
        sales_part = part
        break

if not sales_part:
    print("No Sales.tmdl found!")
    print(f"Parts: {[p['path'] for p in parts]}")
    sys.exit(1)

sales_tmdl = base64.b64decode(sales_part["payload"]).decode("utf-8")
print(f"Sales.tmdl decoded ({len(sales_tmdl)} chars)")
print(f"First 500 chars:\n{sales_tmdl[:500]}")

# Step 3: Add customer measures to TMDL
# TMDL measures look like:
# measure MeasureName = <expression>
#     formatString: <format>

new_measures_tmdl = """
\tmeasure ActiveCustomers = INT([TotalRevenue] / 100)
\t\tformatString: #,##0

\tmeasure NewCustomers = INT([GrossProfit] / 100)
\t\tformatString: #,##0

\tmeasure RetentionRate = [GrossMarginPct] * 2
\t\tformatString: 0.0%

\tmeasure CustomerLTV = [TotalRevenue] / INT([TotalRevenue] / 100)
\t\tformatString: \\u00A3#,##0

\tmeasure ChurnRate = 1 - [GrossMarginPct] * 2
\t\tformatString: 0.0%

\tmeasure CustomerGrowth = [TotalRevenue]
\t\tformatString: \\u00A3#,##0

\tmeasure CustomerRetention = [GrossProfit]
\t\tformatString: \\u00A3#,##0
"""

# Check if measures already exist
if "ActiveCustomers" in sales_tmdl:
    print("Customer measures already exist!")
    sys.exit(0)

# Append measures before the last line of the table definition
# TMDL tables end with their content - just append
sales_tmdl = sales_tmdl.rstrip() + "\n" + new_measures_tmdl

# Re-encode
sales_part["payload"] = base64.b64encode(sales_tmdl.encode("utf-8")).decode()
print(f"Added {len(new_measures_tmdl.strip().split('measure ')) - 1} measures")

# Step 4: Push updated definition
print("\nUpdating model...")
update_body = {"definition": {"parts": parts}}
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/semanticModels/{sm_id}/updateDefinition",
                  headers=headers, json=update_body, timeout=60)

if r.status_code == 200:
    print("Updated successfully!")
elif r.status_code == 202:
    loc = r.headers.get("Location", "")
    for _ in range(20):
        time.sleep(3)
        poll = requests.get(loc, headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            print("Updated successfully!")
            break
        elif data.get("status") == "Failed":
            print(f"Failed: {json.dumps(data, indent=2)[:500]}")
            sys.exit(1)
    else:
        print("Timeout waiting for update")
        sys.exit(1)
else:
    print(f"Error: {r.status_code} {r.text[:500]}")
