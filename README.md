# Qlik Script cli   

## Set-up

### Prerequisites

- Python 3.9 or higher

### 1. Install

1. Clone or download the repo and place it in a logical location, e.g. `C:\Users\<YOU>\AppData\Local\Programs\Qlik_DEV`
2. Double-click `setup.bat` — this sets up the environment and installs the necessary dependencies automatically.
3. Add the `qlik` subfolder to your system PATH, e.g. `C:\Users\<YOU>\AppData\Local\Programs\Qlik_DEV\qlik`
   — this exposes the `qlik` command globally.

### 2. Connect to a Qlik Cloud Tenant

```bash
qlik set_tenant https://{tenant}.{region}.qlikcloud.com
qlik set_tenant_api_key <your-api-key>
qlik get_tenant   # get current tenant URL and API key
```

### 3. Usage — Script

> **Important:** Always run `qlik` from your **project folder**, not from the CLI install directory from step 1.

```bash
qlik get "MyApp"                 # download app script as .qvs files
qlik get_space "space name"      # get all apps in space
qlik set "MyApp"                 # validate & push changes back
qlik load "MyApp"                # reload the app (streams logs)
qlik pub "MyApp"                 # publish to managed space
qlik rem "MyApp"                 # delete local script directory
```

**Typical workflow:**

```bash
qlik get "MyApp"                 # pull script into local .qvs files
# edit locally …
qlik set "MyApp"                 # push changes back
qlik load "MyApp"                # reload to verify
qlik pub "MyApp"                 # publish to managed space
```

### 4. Usage — Master Items

Master items are stored as JSON under `Apps/{appId}/{appName}/masteritems/`.

```bash
qlik get_items "MyApp"           # pull measures + dimensions → masteritems/
qlik set_items "MyApp"           # push (create/update) measures + dimensions from masteritems/
qlik pub_items "MyApp"           # publish shared space app → managed space app
```

**Typical workflow:**

```bash
qlik get_items "MyApp"           # pull current master items from shared space app
# edit measures.json / dimensions.json locally …
qlik set_items "MyApp"           # push back to shared space app
qlik pub_items "MyApp"           # publish shared space app to managed space app
```

**JSON schema — measures.json**

```json
[
  {
    "id":          "abc123",
    "title":       "Total Sales",
    "definition":  "Sum(Sales)",
    "label":       "='Total Sales'",
    "description": "Sum of all sales",
    "fmt":         "#,##0.00",
    "tags":        ["finance"]
  }
]
```

**JSON schema — dimensions.json**

```json
[
  {
    "id":               "def456",
    "title":            "Customer",
    "definition":       "CustomerName",
    "label":            "Customer",
    "label_expression": "='Customer'",
    "description":      "Customer name dimension",
    "tags":             ["crm"]
  }
]
```

> **Duplicate handling:** if the app contains more than one master item with the same title, `set_items` will skip that item and write the conflicting entries to `measures_duplicates.json` / `dimensions_duplicates.json` for manual review.

### 5. Claude Code Skills

Skills in `.claude/skills/` extend Claude Code:

| Skill | Purpose |
|-------|---------|
| **qlik-cli** | Lets Claude invoke the CLI commands (`get`, `set`, `load`, `pub`, `set_tenant`, `get_tenant`, …) on your behalf and manage the full script workflow from within the conversation. |

Skills can also be globally installed in `~/.claude/skills/` to be available in any project.

### 6. Install Syntax Highlighting (Optional)

1. Open Cursor
2. Go to **Extensions** (or press `Ctrl+Shift+X`)
3. Click the **...** menu → **Install from VSIX...**
4. Select: `qlik highlight/gimly81.qlik-0.5.0.vsix`
5. Restart Cursor

### 7. Install Filename Highlighting (Optional)

Install VSCode Icons Theme (`vscode-icons-team.vscode-icons`) and activate it to display Qlik Sense icons for `.qvs` files.
