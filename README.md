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
qlik get_space "My Space"        # fetch all apps in space (script, master items, objects)
# edit locally …
qlik set_script "MyApp"          # push changes back
qlik load_script "MyApp"         # reload to verify
qlik pub_script "MyApp"          # publish to managed space
```

### 4. Usage — Master Items

Master items are stored as JSON under `Apps/{appId}/{appName}/masteritems/`.

```bash
qlik get_app "MyApp"             # pull current master items from shared space app
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

> **ID handling:** When creating a new master item, any `id` you set in the JSON will be overwritten by Qlik's own GUID. If you change an existing item's `id`, Qlik treats it as a brand-new item on the next `set_items` run (the old item remains untouched).

> **Deletion:** Removing an item from the local JSON will not delete it from the app — `set_items` is additive/update-only by design. To delete a master item, do so directly in Qlik, then run `qlik get_app` to sync the local JSON.

> **Duplicate handling:** `set_items` matches by ID when present, falling back to title for new items (no ID yet). If the title fallback finds more than one match in the app, the run is aborted with an error listing the conflicting IDs — resolve the duplicates in `measures.json` / `dimensions.json` and re-run.

### 5. Usage — Flag Items

Highlights chart objects using inline (non-master) measures or dimensions — useful for auditing before migrating expressions to master items.

```bash
qlik flag_items "MyApp"          # visually identify charts not using master items
# review flagged charts in Qlik and update expressions to use master items …
qlik unflag_items "MyApp"        # restore backgrounds once done
```

### 7. Claude Code Skills

Skills in `.claude/skills/` extend Claude Code:

| Skill | Purpose |
|-------|---------|
| **qlik-cli** | Lets Claude invoke the CLI commands (`get`, `set_script`, `load_script`, `pub_script`, `set_tenant`, `get_tenant`, …) on your behalf and manage the full script workflow from within the conversation. |

Skills can also be globally installed in `~/.claude/skills/` to be available in any project.

### 8. Install Syntax Highlighting (Optional)

1. Open Cursor
2. Go to **Extensions** (or press `Ctrl+Shift+X`)
3. Click the **...** menu → **Install from VSIX...**
4. Select: `qlik highlight/gimly81.qlik-0.5.0.vsix`
5. Restart Cursor

### 9. Install Filename Highlighting (Optional)

Install VSCode Icons Theme (`vscode-icons-team.vscode-icons`) and activate it to display Qlik Sense icons for `.qvs` files.
