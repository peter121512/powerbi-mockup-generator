"""Add Customer table to the semantic model using the generated CSV data.

Creates a calculated table from DATATABLE() with realistic customer records,
plus proper DAX measures for KPIs.
"""
import sys, json, time, base64, csv, requests
from pathlib import Path
sys.path.insert(0, "src")
from pbi_gen.deploy.fabric import load_config, get_credential, FABRIC_API_BASE

config = load_config()
credential = get_credential(config)
token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

workspace_id = config["workspace_id"]
sm_id = "b731eda9-c402-42c4-ad27-f4641c7d6bcd"

# Load customer CSV
csv_path = Path("data/customer/Customer.csv")
customers = []
with open(csv_path, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        customers.append(row)

print(f"Loaded {len(customers)} customers from CSV")

# Step 1: Get model definition
print("Getting model definition...")
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/semanticModels/{sm_id}/getDefinition",
                  headers=headers, json={}, timeout=30)
loc = r.headers.get("Location", "")
for _ in range(20):
    time.sleep(3)
    poll = requests.get(loc, headers=headers, timeout=30)
    if poll.json().get("status") == "Succeeded":
        break

r2 = requests.get(f"{loc}/result", headers=headers, timeout=30)
definition = r2.json().get("definition", r2.json())
parts = definition.get("parts", [])
print(f"Got definition with {len(parts)} parts")

# Step 2: Check if Customer table already exists
has_customer = any(p["path"] == "definition/tables/Customer.tmdl" for p in parts)
if has_customer:
    print("Customer table already exists — removing old version")
    parts = [p for p in parts if p["path"] != "definition/tables/Customer.tmdl"]

# Step 3: Build Customer TMDL with DATATABLE and measures
# Use a subset (200 customers) to keep the table manageable
sample = customers[:200]

# Build a compact DATATABLE expression (TMDL requires specific formatting)
# Use 1000 customers for realistic density
sample = customers[:1000]

# Single-line row format for TMDL
row_strs = []
for c in sample:
    is_active = "TRUE" if c["IsActive"] == "True" else "FALSE"
    row_strs.append(
        f'{{"{c["CustomerID"]}", "{c["CustomerName"]}", "{c["JoinDate"]}", '
        f'"{c["Segment"]}", "{c["AcquisitionChannel"]}", "{c["Region"]}", '
        f'{is_active}, "{c["ChurnDate"]}", {c["AnnualValue"]}}}'
    )

datatable_rows = ", ".join(row_strs)
datatable_expr = (
    f'DATATABLE("CustomerID", STRING, "CustomerName", STRING, "JoinDate", STRING, '
    f'"Segment", STRING, "AcquisitionChannel", STRING, "Region", STRING, '
    f'"IsActive", BOOLEAN, "ChurnDate", STRING, "AnnualValue", DOUBLE, '
    f'{{{datatable_rows}}})'
)

customer_tmdl = f'''table Customer
\tlineageTag: a1b2c3d4-e5f6-7890-abcd-ef1234567890

\tcolumn CustomerID
\t\tdataType: string
\t\tlineageTag: b2c3d4e5-f6a7-8901-bcde-f12345678901
\t\tsummarizeBy: none
\t\tsourceColumn: CustomerID

\tcolumn CustomerName
\t\tdataType: string
\t\tlineageTag: c3d4e5f6-a7b8-9012-cdef-123456789012
\t\tsummarizeBy: none
\t\tsourceColumn: CustomerName

\tcolumn JoinDate
\t\tdataType: string
\t\tlineageTag: d4e5f6a7-b8c9-0123-defa-234567890123
\t\tsummarizeBy: none
\t\tsourceColumn: JoinDate

\tcolumn Segment
\t\tdataType: string
\t\tlineageTag: e5f6a7b8-c9d0-1234-efab-345678901234
\t\tsummarizeBy: none
\t\tsourceColumn: Segment

\tcolumn AcquisitionChannel
\t\tdataType: string
\t\tlineageTag: f6a7b8c9-d0e1-2345-fabc-456789012345
\t\tsummarizeBy: none
\t\tsourceColumn: AcquisitionChannel

\tcolumn Region
\t\tdataType: string
\t\tlineageTag: a7b8c9d0-e1f2-3456-abcd-567890123456
\t\tsummarizeBy: none
\t\tsourceColumn: Region

\tcolumn IsActive
\t\tdataType: boolean
\t\tlineageTag: b8c9d0e1-f2a3-4567-bcde-678901234567
\t\tsummarizeBy: none
\t\tsourceColumn: IsActive

\tcolumn ChurnDate
\t\tdataType: string
\t\tlineageTag: c9d0e1f2-a3b4-5678-cdef-789012345678
\t\tsummarizeBy: none
\t\tsourceColumn: ChurnDate

\tcolumn AnnualValue
\t\tdataType: double
\t\tlineageTag: d0e1f2a3-b4c5-6789-defa-890123456789
\t\tsummarizeBy: sum
\t\tsourceColumn: AnnualValue

\tmeasure ActiveCustomers = COUNTROWS(FILTER(Customer, Customer[IsActive] = TRUE()))
\t\tformatString: #,##0

\tmeasure NewCustomers = COUNTROWS(FILTER(Customer, Customer[JoinDate] >= "2023-01-01"))
\t\tformatString: #,##0

\tmeasure RetentionRate = DIVIDE(COUNTROWS(FILTER(Customer, Customer[IsActive] = TRUE())), COUNTROWS(Customer))
\t\tformatString: 0.0%

\tmeasure CustomerLTV = DIVIDE(SUM(Customer[AnnualValue]), COUNTROWS(FILTER(Customer, Customer[IsActive] = TRUE())))
\t\tformatString: \\u00A3#,##0

\tmeasure ChurnRate = DIVIDE(COUNTROWS(FILTER(Customer, Customer[IsActive] = FALSE())), COUNTROWS(Customer))
\t\tformatString: 0.0%

\tmeasure TotalCustomers = COUNTROWS(Customer)
\t\tformatString: #,##0

\tmeasure CustomerGrowth = COUNTROWS(FILTER(Customer, Customer[IsActive] = TRUE()))
\t\tformatString: #,##0

\tmeasure CustomerRetention = COUNTROWS(FILTER(Customer, Customer[IsActive] = TRUE()))
\t\tformatString: #,##0

\tpartition Customer = calculated
\t\tmode: import
\t\tsource = {datatable_expr}
'''

# Step 4: Add Customer table part
parts.append({
    "path": "definition/tables/Customer.tmdl",
    "payload": base64.b64encode(customer_tmdl.encode("utf-8")).decode(),
    "payloadType": "InlineBase64",
})

# Step 5: Remove old proxy measures from Sales table (if they exist)
for part in parts:
    if part["path"] == "definition/tables/Sales.tmdl":
        sales_content = base64.b64decode(part["payload"]).decode("utf-8")
        # Remove the old proxy customer measures
        lines = sales_content.split("\n")
        filtered = []
        skip_measure = False
        for line in lines:
            if any(m in line for m in ["measure ActiveCustomers", "measure NewCustomers",
                                        "measure RetentionRate", "measure CustomerLTV",
                                        "measure ChurnRate", "measure CustomerGrowth",
                                        "measure CustomerRetention"]):
                skip_measure = True
                continue
            if skip_measure:
                if line.startswith("\t\t") and not line.startswith("\t\tmeasure"):
                    continue  # skip formatString/annotation lines
                else:
                    skip_measure = False
            if not skip_measure:
                filtered.append(line)
        part["payload"] = base64.b64encode("\n".join(filtered).encode("utf-8")).decode()
        print("Removed old proxy measures from Sales table")
        break

# Step 6: Update model
print("Updating model definition...")
update_body = {"definition": {"parts": parts}}
r = requests.post(f"{FABRIC_API_BASE}/workspaces/{workspace_id}/semanticModels/{sm_id}/updateDefinition",
                  headers=headers, json=update_body, timeout=60)

if r.status_code == 202:
    loc = r.headers.get("Location", "")
    for _ in range(30):
        time.sleep(3)
        poll = requests.get(loc, headers=headers, timeout=30)
        data = poll.json()
        if data.get("status") == "Succeeded":
            print("Model updated successfully!")
            break
        elif data.get("status") == "Failed":
            print(f"FAILED: {json.dumps(data, indent=2)[:800]}")
            break
    else:
        print("Timeout")
elif r.status_code == 200:
    print("Updated!")
else:
    print(f"Error {r.status_code}: {r.text[:500]}")
